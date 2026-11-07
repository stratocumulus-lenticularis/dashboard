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


def parse(data: dict, cfg: Config) -> Forecast:
    g = data["graph"]
    start = _ms(g["start"], cfg)
    temps = [float(v) for v in g.get("temperatureMean1h", [])]

    # precipitation1h is hourly mm; fall back to summing 10-minute values
    precip = [float(v) for v in g.get("precipitation1h", [])]
    if not precip:
        p10 = g.get("precipitation10m", [])
        precip = [sum(p10[i:i + 6]) for i in range(0, len(p10), 6)]

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
