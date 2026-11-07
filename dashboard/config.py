"""Configuration from environment variables / .env file (stdlib only)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import time
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent

WIDTH = 800
HEIGHT = 480  # landscape only, see PROJECT_CONTEXT.md


def load_env(path: Path | None = None) -> None:
    """Load KEY=VALUE lines into os.environ (existing variables win)."""
    path = path or ROOT / ".env"
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key.strip(), value)


def _int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name) or default)
    except ValueError:
        return default


def _time(name: str, default: str) -> time:
    raw = os.environ.get(name) or default
    try:
        hh, mm = raw.split(":")
        return time(int(hh), int(mm))
    except ValueError:
        hh, mm = default.split(":")
        return time(int(hh), int(mm))


@dataclass(frozen=True)
class Config:
    tz: ZoneInfo
    display_driver: str
    refresh_minutes: int
    sleep_start: time
    sleep_end: time
    log_level: str
    data_dir: Path
    plz: str
    netatmo_client_id: str
    netatmo_client_secret: str
    netatmo_refresh_token: str
    netatmo_device_id: str
    solar_url: str
    solar_token: str
    calendar_ics_url: str
    football_token: str
    arsenal_team_id: str


def load_config() -> Config:
    load_env()
    g = lambda k: os.environ.get(k, "").strip()  # noqa: E731
    return Config(
        tz=ZoneInfo(g("DASHBOARD_TIMEZONE") or "Europe/Berlin"),
        display_driver=g("DISPLAY_DRIVER") or "auto",
        refresh_minutes=max(5, _int("FULL_REFRESH_MINUTES", 30)),
        sleep_start=_time("SLEEP_START", "00:00"),
        sleep_end=_time("SLEEP_END", "06:00"),
        log_level=g("LOG_LEVEL") or "INFO",
        data_dir=ROOT / "data",
        plz=g("PLZ"),
        netatmo_client_id=g("NETATMO_CLIENT_ID"),
        netatmo_client_secret=g("NETATMO_CLIENT_SECRET"),
        netatmo_refresh_token=g("NETATMO_REFRESH_TOKEN"),
        netatmo_device_id=g("NETATMO_DEVICE_ID"),
        solar_url=g("SOLARMANAGER_URL"),
        solar_token=g("SOLARMANAGER_TOKEN"),
        calendar_ics_url=g("GOOGLE_CALENDAR_ICS_URL"),
        football_token=g("FOOTBALL_DATA_TOKEN"),
        arsenal_team_id=g("ARSENAL_TEAM_ID") or "57",
    )
