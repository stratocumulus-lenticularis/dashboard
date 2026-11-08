"""Netatmo weather station (OAuth2 refresh-token flow)."""

from __future__ import annotations

import json
import logging
import time

from .. import net
from ..config import Config
from ..models import Observation

log = logging.getLogger(__name__)

TOKEN_URL = "https://api.netatmo.com/oauth2/token"
STATIONS_URL = "https://api.netatmo.com/api/getstationsdata?get_favorites=false"


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


def _access_token(cfg: Config) -> str:
    resp = net.post_form_json(
        TOKEN_URL,
        {
            "grant_type": "refresh_token",
            "refresh_token": _refresh_token(cfg),
            "client_id": cfg.netatmo_client_id,
            "client_secret": cfg.netatmo_client_secret,
        },
    )
    cfg.data_dir.mkdir(parents=True, exist_ok=True)
    _token_file(cfg).write_text(json.dumps({"refresh_token": resp["refresh_token"]}))
    return resp["access_token"]


def parse(body: dict, device_id: str = "") -> Observation:
    devices = body["body"]["devices"]
    dev = next((d for d in devices if not device_id or d["_id"] == device_id), devices[0])
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
    return obs


def fetch(cfg: Config) -> Observation:
    if not (cfg.netatmo_client_id and cfg.netatmo_client_secret):
        raise ValueError("Netatmo not configured")
    token = _access_token(cfg)
    body = net.get_json(STATIONS_URL, {"Authorization": f"Bearer {token}"})
    log.debug("netatmo fetched at %s", time.strftime("%H:%M"))
    return parse(body, cfg.netatmo_device_id)
