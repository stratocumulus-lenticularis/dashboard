"""Solar Manager live values via the device's "Local API".

Endpoint:  GET https://<device>/v2/point      header  X-API-Key: <key>
Fields (W = instantaneous power, all >= 0):
    pW  PV production      cW  consumption
    bcW battery charging   bdW battery discharging
The grid power is derived (the API has no field for it):
    import - export = cW - pW - bdW + bcW
Battery state of charge is in devices[] of the same response ("soc"); the
device type comes from GET /v2/devices ("type" containing "battery").

SOURCE / ASSUMPTION: field names and endpoints are taken from a third-party
Home Assistant integration (github.com/mbuob/SolarManagerHAIntegration), as
Solar Manager's own API documentation could not be read. Not verified against
your installation - run `python -m dashboard --check` to see the result.
"""

from __future__ import annotations

import json
import logging
import ssl
import urllib.error
from urllib.parse import urlparse

from .. import net
from ..config import Config
from ..models import Energy

log = logging.getLogger(__name__)

WEB_APP_HOSTS = ("cloud.solar-manager.ch", "solar-manager.ch", "www.solar-manager.ch")


def _base(url: str) -> str:
    """'192.168.1.50' / 'https://host' / 'https://host/v2/point' -> 'https://host'."""
    url = url.strip().rstrip("/")
    if "://" not in url:
        url = "https://" + url
    p = urlparse(url)
    if (p.hostname or "") in WEB_APP_HOSTS:
        raise ValueError(
            f"SOLARMANAGER_URL points to the web app ({p.hostname}), not to the API. "
            "Use the address of your Solar Manager device, e.g. 192.168.1.50"
        )
    return f"{p.scheme}://{p.netloc}"


def _num(data: dict, key: str) -> float | None:
    v = data.get(key)
    return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def _battery_soc(point: dict, battery_ids: set[str]) -> float | None:
    """SoC of the battery device. EV chargers also report 'soc', so filter by type."""
    candidates = [d for d in point.get("devices") or [] if isinstance(d.get("soc"), (int, float))]
    if battery_ids:
        candidates = [d for d in candidates if d.get("_id") in battery_ids]
    elif len(candidates) > 1:
        return None  # cannot tell battery and EV apart
    return float(candidates[0]["soc"]) if candidates else None


def parse(point: dict, devices: list[dict] | None = None) -> Energy:
    p, c = _num(point, "pW"), _num(point, "cW")
    bc, bd = _num(point, "bcW"), _num(point, "bdW")
    if p is None and c is None:
        raise ValueError(f"unexpected response, no pW/cW (keys: {sorted(point)[:8]})")
    bc0, bd0 = bc or 0.0, bd or 0.0
    battery_ids = {
        d.get("deviceId") for d in devices or [] if "battery" in str(d.get("type", "")).lower()
    }
    return Energy(
        pv_w=p,
        consumption_w=c,
        grid_w=None if p is None or c is None else c - p - bd0 + bc0,  # >0 import
        battery_w=None if bc is None and bd is None else bc0 - bd0,  # >0 charging
        battery_soc=_battery_soc(point, battery_ids),
    )


def _get(url: str, cfg: Config):
    headers = {"X-API-Key": cfg.solar_token} if cfg.solar_token else {}
    try:
        return net.get_json(url, headers, verify=cfg.solar_verify_ssl)
    except urllib.error.HTTPError as exc:
        hint = {
            401: "API key rejected",
            403: "API key rejected",
            404: "wrong address/path",
        }.get(exc.code, "")
        raise RuntimeError(f"HTTP {exc.code} from {url} {hint}".strip()) from exc
    except urllib.error.URLError as exc:
        if isinstance(exc.reason, ssl.SSLCertVerificationError):
            raise RuntimeError(
                "certificate not trusted - the device uses a self-signed certificate: "
                "set SOLARMANAGER_VERIFY_SSL=0 in .env"
            ) from exc
        raise
    except json.JSONDecodeError as exc:  # a ValueError: must not look like "not configured"
        raise RuntimeError(f"{url} did not return JSON (wrong address?)") from exc


def fetch(cfg: Config) -> Energy:
    if not cfg.solar_url:
        raise ValueError("Solar Manager not configured")
    base = _base(cfg.solar_url)
    point = _get(base + "/v2/point", cfg)
    try:
        devices = _get(base + "/v2/devices", cfg)
    except Exception as exc:  # noqa: BLE001 - only needed to tell battery from EV
        log.info("solarmanager: device list unavailable (%s)", exc)
        devices = None
    return parse(point, devices if isinstance(devices, list) else None)
