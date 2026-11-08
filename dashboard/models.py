"""Plain data containers passed from sources to renderers."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone


@dataclass
class Observation:
    """Current readings of the own Netatmo station.

    The station measures temperature, humidity and pressure only
    (no wind, no rain) - those come from the MeteoSwiss forecast.
    """

    temperature: float | None = None
    humidity: int | None = None
    pressure: float | None = None  # hPa, sea level
    t_min: float | None = None  # today, outdoor module
    t_max: float | None = None
    pressure_trend: str | None = None  # "up" | "down" | "stable"


@dataclass
class DayForecast:
    day: datetime
    t_min: float | None
    t_max: float | None
    precip_mm: float | None
    sunshine_h: float | None = None  # summed from the hourly series


@dataclass
class Forecast:
    """MeteoSwiss forecast: hourly series (all aligned to `start`) + daily summary."""

    start: datetime
    temps: list[float] = field(default_factory=list)  # deg C
    precip: list[float] = field(default_factory=list)  # mm per hour
    days: list[DayForecast] = field(default_factory=list)
    sunrise: datetime | None = None
    sunset: datetime | None = None
    sun: list[float] = field(default_factory=list)  # sunshine minutes per hour (0-60)
    wind: list[float] = field(default_factory=list)  # mean wind, km/h
    gust: list[float] = field(default_factory=list)  # gusts, km/h

    def time_at(self, i: int) -> datetime:
        """Local time of hourly index i (absolute-time arithmetic, DST safe)."""
        utc = self.start.astimezone(timezone.utc) + timedelta(hours=i)
        return utc.astimezone(self.start.tzinfo)


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
