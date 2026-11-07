"""Plain data containers passed from sources to renderers."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Observation:
    """Current readings of the own Netatmo station."""

    temperature: float | None = None
    humidity: int | None = None
    pressure: float | None = None
    rain_1h: float | None = None
    rain_24h: float | None = None
    wind_kmh: float | None = None
    gust_kmh: float | None = None


@dataclass
class DayForecast:
    day: datetime
    t_min: float | None
    t_max: float | None
    precip_mm: float | None


@dataclass
class Forecast:
    """MeteoSwiss forecast: hourly series (next hours) plus daily summary."""

    start: datetime
    temps: list[float] = field(default_factory=list)  # hourly, from `start`
    precip: list[float] = field(default_factory=list)  # mm per hour
    days: list[DayForecast] = field(default_factory=list)
    sunrise: datetime | None = None
    sunset: datetime | None = None


@dataclass
class Energy:
    """Solar Manager live values. Power in W, soc in %."""

    pv_w: float | None = None
    consumption_w: float | None = None
    grid_w: float | None = None  # >0 import, <0 export
    battery_w: float | None = None  # >0 charging, <0 discharging
    battery_soc: float | None = None


@dataclass
class Event:
    start: datetime | None  # None = all day
    title: str


@dataclass
class Match:
    kickoff: datetime
    home: str
    away: str
    competition: str = ""
