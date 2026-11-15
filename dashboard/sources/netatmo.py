"""Netatmo weather station (OAuth2 refresh-token flow)."""

from __future__ import annotations

import json
import logging
import os
import urllib.error
from datetime import datetime, timezone

from .. import net
from ..config import Config
from ..models import Observation

log = logging.getLogger(__name__)

TOKEN_URL = "https://api.netatmo.com/oauth2/token"
STATIONS_URL = "https://api.netatmo.com/api/getstationsdata?get_favorites=false"

# The outdoor module reports every ~10 min. Netatmo keeps returning the LAST
# reading when a module is offline, so the measurement time must be checked.
MAX_AGE_S = 45 * 60


class StaleStationData(Exception):
    """The station answered, but its measurement is too old to show."""


def _token_file(cfg: Config):
    return cfg.data_dir / "netatmo_token.json"


def _refresh_token(cfg: Config) -> str:
    """Netatmo rotates refresh tokens, so the newest one is kept on disk."""
    f = _token_file(cfg)
    if f.is_file():
        try:
            return json.loads(f.read_text())["refresh_token"]
        except (ValueError, KeyError):
            pass
    return cfg.netatmo_refresh_token


def _save_refresh_token(cfg: Config, token: str) -> None:
    """Atomic write: a crash/power loss must never leave a half-written file."""
    cfg.data_dir.mkdir(parents=True, exist_ok=True)
    f = _token_file(cfg)
    tmp = f.with_suffix(".tmp")
    tmp.write_text(json.dumps({"refresh_token": token}))
    os.replace(tmp, f)


def _access_token(cfg: Config) -> str:
    # newest saved token first; the one from .env is a fallback (e.g. after
    # the user generated a fresh token and put it into .env)
    candidates = [_refresh_token(cfg)]
    if cfg.netatmo_refresh_token and cfg.netatmo_refresh_token not in candidates:
        candidates.append(cfg.netatmo_refresh_token)

    last_error: Exception | None = None
    for token in candidates:
        try:
            resp = net.post_form_json(
                TOKEN_URL,
                {
                    "grant_type": "refresh_token",
                    "refresh_token": token,
                    "client_id": cfg.netatmo_client_id,
                    "client_secret": cfg.netatmo_client_secret,
                },
            )
        except urllib.error.HTTPError as exc:
            body = exc.read()[:200].decode("utf-8", "replace")
            log.warning("netatmo token refresh rejected: HTTP %s %s", exc.code, body)
            last_error = exc
            continue
        _save_refresh_token(cfg, resp["refresh_token"])
        return resp["access_token"]
    raise last_error or RuntimeError("no Netatmo refresh token available")


def parse(body: dict, device_id: str = "") -> Observation:
    devices = body["body"]["devices"]
    wanted = device_id.strip().lower()
    dev = next((d for d in devices if not wanted or d["_id"].lower() == wanted), None)
    if dev is None:
        log.warning(
            "NETATMO_DEVICE_ID %r matches no station (it must be the base station's "
            "MAC address, see `python -m dashboard --check`) - using the first station",
            device_id,
        )
        dev = devices[0]
    obs = Observation()
    # base station: pressure ("Pressure" = sea level, the usual weather value)
    base = dev.get("dashboard_data", {})
    obs.pressure = base.get("Pressure") or base.get("AbsolutePressure")
    obs.pressure_trend = base.get("pressure_trend")
    # outdoor module (NAModule1): temperature and humidity. The station has
    # no wind/rain gauge - wind and rain come from MeteoSwiss.
    for mod in dev.get("modules", []):
        if mod.get("type") == "NAModule1" and obs.temperature is None:
            dd = mod.get("dashboard_data", {})
            obs.temperature = dd.get("Temperature")
            obs.humidity = dd.get("Humidity")
            obs.t_min = dd.get("min_temp")
            obs.t_max = dd.get("max_temp")
            if dd.get("time_utc"):
                obs.measured_at = datetime.fromtimestamp(dd["time_utc"], tz=timezone.utc)
    return obs


def fetch(cfg: Config) -> Observation:
    if not (cfg.netatmo_client_id and cfg.netatmo_client_secret):
        raise ValueError("Netatmo not configured")
    token = _access_token(cfg)
    body = net.get_json(STATIONS_URL, {"Authorization": f"Bearer {token}"})
    obs = parse(body, cfg.netatmo_device_id)
    if obs.temperature is None:
        raise StaleStationData("no outdoor module (NAModule1) found in station data")
    if obs.measured_at is not None:
        age = (datetime.now(timezone.utc) - obs.measured_at).total_seconds()
        log.info("netatmo: outdoor measurement is %d min old", age // 60)
        if age > MAX_AGE_S:
            raise StaleStationData(
                f"outdoor measurement is {int(age // 60)} min old "
                "(module offline? check battery / radio range)"
            )
    return obs
