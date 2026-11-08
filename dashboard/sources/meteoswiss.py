"""MeteoSwiss app endpoint (unofficial, no key needed)."""

from __future__ import annotations

from datetime import datetime, timezone

from .. import net
from ..config import Config
from ..models import DayForecast, Forecast

URL = "https://app-prod-ws.meteoswiss-app.ch/v1/plzDetail?plz={plz}"


def _plz6(plz: str) -> str:
    plz = plz.strip()
    if len(plz) == 4:
        return plz + "00"
    return plz


def _ms(value: int, cfg: Config) -> datetime:
    return datetime.fromtimestamp(value / 1000, tz=timezone.utc).astimezone(cfg.tz)


def hourly_precip(g: dict, cfg: Config) -> list[float]:
    """Hourly rain (mm), aligned with graph.start like the temperature series.

    MeteoSwiss delivers rain in two consecutive parts:
      - precipitation10m: 10-minute values from `start` up to
        `startLowResolution` (a window of roughly 22-27 h that changes
        during the day)
      - precipitation1h:  hourly values beginning AT `startLowResolution`
    The 1h series therefore does NOT begin at `start` (unlike temperature).
    Both parts are joined here by timestamp, so the result has one value
    per hour starting at `start`, like temperatureMean1h.
    """
    p10 = [float(v) for v in g.get("precipitation10m", [])]
    p1h = [float(v) for v in g.get("precipitation1h", [])]
    n_temps = len(g.get("temperatureMean1h", [])) or len(p1h)

    low = g.get("startLowResolution")
    head_hours = round((low - g["start"]) / 3_600_000) if low else 0
    head_hours = max(0, min(head_hours, n_temps))

    head = []
    for h in range(head_hours):
        chunk = p10[h * 6:h * 6 + 6]  # missing values (partial hour) count as 0
        head.append(round(sum(chunk), 2))
    return (head + p1h)[:n_temps]


def parse(data: dict, cfg: Config) -> Forecast:
    g = data["graph"]
    start = _ms(g["start"], cfg)
    temps = [float(v) for v in g.get("temperatureMean1h", [])]

    precip = hourly_precip(g, cfg)

    days = []
    for d in data.get("forecast", []):
        day = datetime.strptime(d["dayDate"], "%Y-%m-%d").replace(tzinfo=cfg.tz)
        days.append(
            DayForecast(
                day=day,
                t_min=d.get("temperatureMin"),
                t_max=d.get("temperatureMax"),
                precip_mm=d.get("precipitation"),
            )
        )

    sunrise = sunset = None
    if g.get("sunrise") and g.get("sunset"):
        sunrise, sunset = _ms(g["sunrise"][0], cfg), _ms(g["sunset"][0], cfg)

    return Forecast(start, temps, precip, days, sunrise, sunset)


def fetch(cfg: Config) -> Forecast:
    if not cfg.plz:
        raise ValueError("PLZ not configured")
    data = net.get_json(URL.format(plz=_plz6(cfg.plz)))
    return parse(data, cfg)
