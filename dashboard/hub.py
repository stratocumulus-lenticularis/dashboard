"""Fetches all sources; a failing source never breaks the dashboard.

On error the last good value is kept and flagged as stale, so the renderer can
show it with its "Stand HH:MM" timestamp.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from typing import Any, Callable

from .config import Config
from .sources import arsenal, calendar_ics, meteoswiss, netatmo, solarmanager

log = logging.getLogger(__name__)

# name -> fetch function. Add new sources here.
SOURCES: dict[str, Callable[[Config], Any]] = {
    "observation": netatmo.fetch,
    "forecast": meteoswiss.fetch,
    "energy": solarmanager.fetch,
    "calendar": calendar_ics.fetch,
    "match": arsenal.fetch,
}


@dataclass
class Snapshot:
    value: Any = None
    fetched_at: datetime | None = None  # time of last SUCCESSFUL fetch
    stale: bool = True  # True if the latest attempt failed / never succeeded
    error: str = ""


class Hub:
    def __init__(self, cfg: Config) -> None:
        self.cfg = cfg
        self.data: dict[str, Snapshot] = {name: Snapshot() for name in SOURCES}

    def refresh(self) -> dict[str, Snapshot]:
        for name, fetch in SOURCES.items():
            snap = self.data[name]
            try:
                snap.value = fetch(self.cfg)
                snap.fetched_at = datetime.now(self.cfg.tz)
                snap.stale, snap.error = False, ""
            except Exception as exc:  # noqa: BLE001 - isolate every source
                snap.stale, snap.error = True, f"{type(exc).__name__}: {exc}"
                log.warning("source %s failed: %s", name, snap.error)
        return self.data


# A failed source keeps showing its last value, but only up to this age.
# Older data is removed by expire() so outdated numbers never look current.
MAX_AGE = {
    "observation": timedelta(hours=3),  # own station
    "energy": timedelta(minutes=90),  # live PV values
    "forecast": timedelta(hours=24),  # MeteoSwiss
    "match": timedelta(days=3),
}


def is_expired(name: str, snap: Snapshot, now: datetime) -> bool:
    """True if `snap` is a failed fetch whose old value is too old to show."""
    if not snap.stale or snap.value is None or snap.fetched_at is None:
        return False
    if name == "calendar":  # "today's events" are only valid on the day fetched
        return snap.fetched_at.date() != now.date()
    if name == "match" and snap.value.kickoff < now:  # game already played
        return True
    limit = MAX_AGE.get(name)
    return limit is not None and now - snap.fetched_at > limit


def expire(data: dict[str, Snapshot], now: datetime) -> dict[str, Snapshot]:
    """Copy of `data` with too-old values removed (fetched_at is kept)."""
    return {
        name: replace(snap, value=None) if is_expired(name, snap, now) else snap
        for name, snap in data.items()
    }
