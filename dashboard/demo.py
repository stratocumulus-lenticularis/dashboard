"""Synthetic sample data so layouts can be previewed without any API access."""

from __future__ import annotations

import math
from datetime import datetime, timedelta

from .hub import Snapshot
from .models import DayForecast, Energy, Event, Forecast, Match, Observation


def sample(now: datetime) -> dict[str, Snapshot]:
    def ok(v):
        return Snapshot(v, now, False)

    start = now.replace(minute=0, second=0, microsecond=0) - timedelta(hours=1)
    n = 72
    temps = [8 + 5 * math.sin((i - 8) / 24 * 2 * math.pi) for i in range(n)]
    rain = [1.2 if 20 <= i < 26 else (0.3 if 40 <= i < 43 else 0.0) for i in range(n)]
    # sunshine only between ~08 and ~16 o'clock, partly cloudy on day 2
    sun = [0.0] * n
    for i in range(n):
        hour = (start.hour + i) % 24
        if 8 <= hour <= 16:
            sun[i] = 60.0 if i < 24 else (25.0 if i < 48 else 0.0)
    wind = [8 + 6 * math.sin(i / 7) for i in range(n)]
    gust = [w + 6 + (i % 5) for i, w in enumerate(wind)]
    sun_h = [5.0, 3.0, 0.0, 1.5, 4.0, 6.5]
    days = [
        DayForecast(now + timedelta(days=i), 6 + i, 12 + i, p, s)
        for i, (p, s) in enumerate(zip([0.1, 0.0, 9.8, 17.3, 2.5, 2.3], sun_h))
    ]
    return {
        "observation": ok(Observation(9.6, 82, 1012, 3.0, 12.0, "stable")),
        "forecast": ok(Forecast(start, temps, rain, days, sun=sun, wind=wind, gust=gust)),
        "energy": ok(Energy(3420, 910, -2510, 1400, 64)),
        "calendar": ok([
            Event(None, "Schulfest Elternabend"),
            Event(now.replace(hour=9, minute=0), "Zahnarzt Anna"),
            Event(now.replace(hour=15, minute=30), "Fussballtraining"),
            Event(now.replace(hour=19, minute=0), "Elternabend Gymnasium"),
        ]),
        "match": ok(Match(now + timedelta(days=3, hours=2), "Arsenal", "Chelsea")),
    }
