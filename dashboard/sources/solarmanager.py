"""Solar Manager live values via the CLOUD API (cloud.solar-manager.ch).

Source of truth: Solar Manager's public Swagger spec
https://cloud.solar-manager.ch/solarManager/swagger.json  (v1.91.4)

    auth      header  x-api-key: <key from https://web.solar-manager.ch/cloud-api-keys>
    plant id  GET /v1/users                      -> [{"sm_id": ...}, ...]
    live      GET /v3/users/{smId}/data/stream   -> pW, cW, soc, bcW, bdW, iW, eW, devices[]

Fields (W = instantaneous power, >= 0):
    pW  PV production         cW  consumption
    bcW battery charging      bdW battery discharging     soc  battery charge in %
    iW  grid import           eW  grid export

Only the "read" scope is needed. The key is sent in every request (header
x-api-key). Do NOT send it to /v3/auth/refresh: that endpoint would rotate it.
"""

from __future__ import annotations

import json
import logging
import urllib.error

from .. import net
from ..config import Config
from ..models import Energy

log = logging.getLogger(__name__)

BASE = "https://cloud.solar-manager.ch"
_sm_id_cache: dict[str, str] = {}  # api key -> sm_id (looked up once per process)


def _get(path: str, cfg: Config):
    try:
        return net.get_json(BASE + path, {"x-api-key": cfg.solar_token, "Accept": "application/json"})
    except urllib.error.HTTPError as exc:
        hint = {
            401: "API key rejected - check SOLARMANAGER_TOKEN",
            403: "API key lacks the 'read' scope or the plant",
            404: "plant (sm_id) not found",
            429: "rate limit - try again later",
        }.get(exc.code, "")
        raise RuntimeError(f"HTTP {exc.code} for {path}: {hint}".rstrip(": ")) from exc
    except json.JSONDecodeError as exc:  # a ValueError, but NOT "not configured"
        raise RuntimeError(f"{path} did not return JSON") from exc


def _sm_id(cfg: Config) -> str:
    if cfg.solar_sm_id:
        return cfg.solar_sm_id
    if cfg.solar_token in _sm_id_cache:
        return _sm_id_cache[cfg.solar_token]
    users = _get("/v1/users", cfg)
    ids = [u["sm_id"] for u in users if isinstance(u, dict) and u.get("sm_id")]
    if not ids:
        raise RuntimeError("no plant (sm_id) found for this API key")
    if len(ids) > 1:
        log.warning("several plants found (%s) - using the first; set SOLARMANAGER_SM_ID", ids)
    _sm_id_cache[cfg.solar_token] = ids[0]
    return ids[0]


def _num(data: dict, key: str) -> float | None:
    v = data.get(key)
    return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def parse(data: dict) -> Energy:
    p, c = _num(data, "pW"), _num(data, "cW")
    if p is None and c is None:
        raise RuntimeError(f"unexpected response, no pW/cW (keys: {sorted(data)[:10]})")
    bc, bd = _num(data, "bcW"), _num(data, "bdW")
    imp, exp = _num(data, "iW"), _num(data, "eW")

    if imp is not None or exp is not None:  # measured at the grid connection
        grid = (imp or 0.0) - (exp or 0.0)
    elif p is not None and c is not None:  # fallback: balance of the other flows
        grid = c - p - (bd or 0.0) + (bc or 0.0)
    else:
        grid = None
    battery = None if bc is None and bd is None else (bc or 0.0) - (bd or 0.0)
    return Energy(pv_w=p, consumption_w=c, grid_w=grid, battery_w=battery,
                  battery_soc=_num(data, "soc"))


def fetch(cfg: Config) -> Energy:
    if not cfg.solar_token:
        raise ValueError("Solar Manager not configured")
    data = _get(f"/v3/users/{_sm_id(cfg)}/data/stream", cfg)
    if isinstance(data, list) and data:
        data = data[0]
    return parse(data)
