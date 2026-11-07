"""Fetches all sources; a failing source never breaks the dashboard.

On error the last good value is kept and flagged as stale, so the renderer can
show it with its "Stand HH:MM" timestamp.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
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
