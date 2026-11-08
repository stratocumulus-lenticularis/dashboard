"""Weather panels.

- current():  own Netatmo station - temperature, humidity, pressure
- chart():    MeteoSwiss, next 48 h on ONE time axis:
                temperature line + rain bars, sunshine strip, wind strip
- outlook():  MeteoSwiss, next 5 days: temperature, sunshine, rain
"""

from __future__ import annotations

import math
from datetime import datetime

from .util import BLACK, NA, WD_SHORT, WHITE, heading, num, stale_note, text, text_w

Box = tuple[int, int, int, int]  # x, y, w, h

HOURS = 48
TREND = {"up": "steigend", "down": "fallend", "stable": "stabil"}


def current(draw, box: Box, snap) -> None:
    x, y, w, h = box
    y = heading(draw, x, y, w, "Draußen")
    stale_note(draw, x + w, box[1] + 2, snap)
    o = snap.value
    if o is None:
        text(draw, (x, y + 10), "keine Daten", 22)
        return
    text(draw, (x, y - 4), num(o.temperature, 1, "°"), 56, bold=True)

    if o.t_min is not None and o.t_max is not None:
        minmax = f"{num(o.t_min, 0, '°')} / {num(o.t_max, 0, '°')}"
    else:
        minmax = NA
    rows = [
        ("Min / Max", minmax),
        ("Feuchte", num(o.humidity, 0, " %")),
        ("Druck", num(o.pressure, 0, " hPa")),
        ("Tendenz", TREND.get(o.pressure_trend or "", NA)),
    ]
    ry = y + 62
    for label, val in rows:
        text(draw, (x, ry), label, 18)
        text(draw, (x + w, ry), val, 18, bold=True, anchor="ra")
        ry += 22


def _legend(draw, x: int, y: int) -> None:
    draw.line((x, y + 8, x + 16, y + 8), fill=BLACK, width=3)
    text(draw, (x + 21, y), "Temperatur", 13)
    rx = x + 21 + text_w(draw, "Temperatur", 13) + 14
    draw.rectangle((rx, y + 3, rx + 7, y + 13), fill=BLACK)
    text(draw, (rx + 12, y), "Regen", 13)


def _dotted_h(draw, x0: float, x1: float, y: float) -> None:
    for gx in range(int(x0), int(x1), 6):
        draw.point((gx, int(y)), fill=BLACK)


def chart(draw, box: Box, snap, now: datetime) -> None:
    """Next 48 h. Strips from top: temperature+rain, sunshine, wind."""
    x, y0, w, h = box
    y = heading(draw, x, y0, w, "Prognose 48 Stunden")
    _legend(draw, x + 190, y0 + 2)
    stale_note(draw, x + w, y0 + 2, snap)
    f = snap.value
    if f is None or not f.temps:
        text(draw, (x, y + 10), "keine Daten", 22)
        return

    first = max(0, int((now - f.start).total_seconds() // 3600))
    n = min(HOURS, len(f.temps) - first)
    if n < 2:
        return
    sl = slice(first, first + n)
    temps, rain = f.temps[sl], f.precip[sl]
    sun, wind, gust = f.sun[sl], f.wind[sl], f.gust[sl]

    # geometry (all strips share the x axis)
    left, right = x + 52, x + w - 4  # left margin holds the labels
    bottom = y0 + h - 18  # x axis; hour labels below
    wind_top = bottom - 30
    sun_bottom = wind_top - 5
    sun_top = sun_bottom - 12
    plot_top = y + 4
    plot_bottom = sun_top - 6
    step = (right - left) / (n - 1)

    # midnight separators through all strips
    for i in range(n):
        if f.time_at(first + i).hour == 0:
            gx = int(left + i * step)
            for gy in range(plot_top, bottom, 4):
                draw.point((gx, gy), fill=BLACK)

    _draw_temp_rain(draw, temps, rain, left, right, step, plot_top, plot_bottom)
    _draw_sun(draw, sun, left, right, step, sun_top, sun_bottom)
    _draw_wind(draw, wind, gust, left, right, step, wind_top, bottom)

    # x axis: tick + label every 6 h, weekday at midnight
    draw.line((left, bottom, right, bottom), fill=BLACK)
    for i in range(n):
        t = f.time_at(first + i)
        if t.hour % 6 == 0:
            gx = left + i * step
            draw.line((gx, bottom, gx, bottom + (6 if t.hour == 0 else 3)), fill=BLACK)
            label = WD_SHORT[t.weekday()] if t.hour == 0 else f"{t.hour}"
            text(draw, (gx, bottom + 5), label, 13, bold=t.hour == 0, anchor="ma")


def _draw_temp_rain(draw, temps, rain, left, right, step, top, bottom) -> None:
    lo = math.floor(min(temps) / 2) * 2
    hi = math.ceil(max(temps) / 2) * 2
    if hi - lo < 4:
        hi = lo + 4

    def ty(t: float) -> float:
        return bottom - (t - lo) / (hi - lo) * (bottom - top)

    for t in (lo, (lo + hi) // 2, hi):
        text(draw, (left - 6, ty(t)), f"{t}°", 13, anchor="rm")
        _dotted_h(draw, left, right, ty(t))

    max_bar = (bottom - top) * 0.45  # 2 mm/h = 45 % of the plot height
    for i, mm in enumerate(rain):
        if mm and mm > 0:
            bh = max(2, min(max_bar, mm / 2 * max_bar))
            bx = left + i * step
            draw.rectangle((bx - step / 2 + 1, bottom - bh, bx + step / 2 - 1, bottom), fill=BLACK)

    pts = [(left + i * step, ty(t)) for i, t in enumerate(temps)]
    draw.line(pts, fill=WHITE, width=6)  # halo keeps the line visible over bars
    draw.line(pts, fill=BLACK, width=3)


def _draw_sun(draw, sun, left, right, step, top, bottom) -> None:
    """Bar height = share of the hour with sunshine (60 min = full height)."""
    text(draw, (left - 6, (top + bottom) / 2), "Sonne", 13, anchor="rm")
    draw.line((left, bottom, right, bottom), fill=BLACK)
    for i, minutes in enumerate(sun):
        if minutes and minutes > 0:
            bh = max(1, round((bottom - top) * min(minutes, 60) / 60))
            bx = left + i * step
            draw.rectangle((bx - step / 2 + 1, bottom - bh, bx + step / 2 - 1, bottom), fill=BLACK)


def _draw_wind(draw, wind, gust, left, right, step, top, bottom) -> None:
    """Mean wind as a line, gusts as small squares. Scale in km/h."""
    if len(wind) < 2:
        return
    peak = max(max(wind), max(gust, default=0))
    vmax = max(20, int(math.ceil(peak / 10.0)) * 10)

    def wy(v: float) -> float:
        return bottom - min(v, vmax) / vmax * (bottom - top)

    _dotted_h(draw, left, right, top)
    text(draw, (left - 6, top), f"{vmax} km/h", 11, anchor="rt")  # scale maximum
    text(draw, (left - 6, bottom), "Wind", 13, anchor="rb")
    for i, v in enumerate(gust):
        cx, cy = left + i * step, wy(v)
        draw.rectangle((cx - 1, cy - 1, cx + 1, cy + 1), fill=BLACK)
    draw.line([(left + i * step, wy(v)) for i, v in enumerate(wind)], fill=BLACK, width=2)


def outlook(draw, box: Box, snap) -> None:
    x, y, w, h = box
    y = heading(draw, x, y, w, "Aussichten")
    stale_note(draw, x + w, box[1] + 2, snap)
    f = snap.value
    if f is None or not f.days:
        text(draw, (x, y + 10), "keine Daten", 22)
        return

    # columns: weekday | temperature | sunshine (right-aligned) | rain (right-aligned)
    # the rain column needs ~65 px ("9.8 mm"), so the sunshine column ends 90 px
    # before the right edge to leave a visible gap
    sun_x = x + w - 90
    text(draw, (x + 40, y), "Temp.", 13)
    text(draw, (sun_x, y), "Sonne", 13, anchor="ra")
    text(draw, (x + w, y), "Regen", 13, anchor="ra")
    y += 18
    for d in f.days[1:6]:  # tomorrow + 4 days
        text(draw, (x, y), WD_SHORT[d.day.weekday()], 20, bold=True)
        text(draw, (x + 40, y + 1), f"{num(d.t_min, 0)}/{num(d.t_max, 0)}°", 19)
        text(draw, (sun_x, y + 2), num(d.sunshine_h, 0, " h"), 18, anchor="ra")
        mm = d.precip_mm
        if mm is None:
            rain = NA
        elif mm < 0.1:
            rain = "0 mm"
        else:
            rain = num(mm, 0 if mm >= 10 else 1, " mm")
        text(draw, (x + w, y + 2), rain, 18, anchor="ra")
        y += 27
