"""Diagnostics: python -m dashboard --check

Fetches every source once and prints what came back (no display needed).
For Netatmo it also lists all stations/modules with the age of their last
measurement, to see whether the right module is being read.
"""

from __future__ import annotations

import time
import urllib.error
from datetime import datetime, timezone

from . import net
from .config import Config
from .hub import SOURCES
from .sources import netatmo


def _age(ts: int | None) -> str:
    if not ts:
        return "unknown"
    minutes = int((time.time() - ts) // 60)
    return f"{minutes} min ago" if minutes < 180 else f"{minutes // 60} h ago"


def _netatmo_overview(cfg: Config) -> None:
    print("\n--- Netatmo: all stations and modules on this account ---")
    if not (cfg.netatmo_client_id and cfg.netatmo_client_secret):
        print("skipped (Netatmo not configured)")
        return
    try:
        token = netatmo._access_token(cfg)
        body = net.get_json(netatmo.STATIONS_URL, {"Authorization": f"Bearer {token}"})
    except urllib.error.HTTPError as exc:
        print(f"request failed: HTTP {exc.code} {exc.read()[:200]!r}")
        return
    except Exception as exc:  # noqa: BLE001
        print(f"request failed: {type(exc).__name__}: {exc}")
        return

    devices = body["body"]["devices"]
    print(f"{len(devices)} station(s); NETATMO_DEVICE_ID is "
          f"{'set' if cfg.netatmo_device_id else 'NOT set (first station is used)'}")
    for n, dev in enumerate(devices):
        mark = "<- used" if (not cfg.netatmo_device_id and n == 0) or dev["_id"] == cfg.netatmo_device_id else ""
        dd = dev.get("dashboard_data", {})
        print(f"\nstation {n}: {dev.get('station_name') or dev.get('module_name', '?')} "
              f"{mark}\n  NETATMO_DEVICE_ID={dev['_id']}")
        print(f"  base   reachable={dev.get('reachable')} "
              f"last measurement {_age(dd.get('time_utc'))} "
              f"pressure={dd.get('Pressure')}")
        for mod in dev.get("modules", []):
            md = mod.get("dashboard_data", {})
            print(f"  {mod.get('type'):9} '{mod.get('module_name', '?')}' reachable={mod.get('reachable')} "
                  f"battery={mod.get('battery_percent')}% last measurement {_age(md.get('time_utc'))} "
                  f"temp={md.get('Temperature')} hum={md.get('Humidity')}")


def run(cfg: Config) -> None:
    now = datetime.now(cfg.tz)
    print(f"time now: {now:%Y-%m-%d %H:%M:%S %Z} (check that this is correct!)")
    for name, fetch in SOURCES.items():
        print(f"\n--- {name} ---")
        started = time.time()
        try:
            value = fetch(cfg)
        except Exception as exc:  # noqa: BLE001
            print(f"FAILED: {type(exc).__name__}: {exc}")
            continue
        print(f"OK ({time.time() - started:.1f} s)")
        if name == "observation":
            age = "unknown"
            if value.measured_at:
                age = f"{int((datetime.now(timezone.utc) - value.measured_at).total_seconds() // 60)} min"
            print(f"  temperature={value.temperature} humidity={value.humidity} "
                  f"pressure={value.pressure} min/max={value.t_min}/{value.t_max} measurement age={age}")
        elif name == "forecast":
            print(f"  start={value.start:%Y-%m-%d %H:%M} hours={len(value.temps)} days={len(value.days)}")
        elif name == "energy":
            print(f"  {value}")
        elif name == "calendar":
            print(f"  {len(value)} event(s) today")
        elif name == "match":
            print(f"  {value}")
    _netatmo_overview(cfg)
