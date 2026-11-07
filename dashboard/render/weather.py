"""Weather panels: current observation, 48 h chart, daily outlook."""

from __future__ import annotations

from datetime import datetime, timedelta

from .util import BLACK, NA, WD_SHORT, heading, num, stale_note, text, text_w, WHITE

Box = tuple[int, int, int, int]  # x, y, w, h


def current(draw, box: Box, snap) -> None:
    x, y, w, h = box
    y = heading(draw, x, y, w, "Draußen")
    stale_note(draw, x + w, box[1] + 2, snap)
    o = snap.value
    if o is None:
        text(draw, (x, y + 10), "keine Daten", 22)
        return
    text(draw, (x, y - 4), num(o.temperature, 1, "°"), 56, bold=True)
    rows = [
        ("Feuchte", num(o.humidity, 0, " %")),
        ("Regen 24h", num(o.rain_24h, 1, " mm")),
        ("Wind", num(o.wind_kmh, 0, " km/h")),
        ("Druck", num(o.pressure, 0, " hPa")),
    ]
    ry = y + 64
    for label, val in rows:
        text(draw, (x, ry), label, 18)
        text(draw, (x + w, ry), val, 18, bold=True, anchor="ra")
        ry += 23


def chart(draw, box: Box, snap, now: datetime) -> None:
    """Next 48 h: temperature line, rain bars, day separators."""
    x, y, w, h = box
    y = heading(draw, x, y, w, "Prognose 48 Stunden")
    stale_note(draw, x + w, box[1] + 2, snap)
    f = snap.value
    if f is None or not f.temps:
        text(draw, (x, y + 10), "keine Daten", 22)
        return

    hours = 48
    first = max(0, int((now - f.start).total_seconds() // 3600))
    temps = f.temps[first:first + hours]
    rain = f.precip[first:first + hours]
    if len(temps) < 2:
        return
    t0 = f.start + timedelta(hours=first)

    left, right = x + 34, x + w - 4  # room for y labels
    top, bottom = y + 6, box[1] + h - 20  # room for x labels
    lo, hi = min(temps), max(temps)
    lo, hi = int(lo // 2 * 2) - 2, int(-(-hi // 2) * 2) + 2  # round to even degrees
    span = max(1, hi - lo)
    step = (right - left) / (len(temps) - 1)

    def py(t: float) -> float:
        return bottom - (t - lo) / span * (bottom - top)

    # y axis: 3 labels + light dotted grid
    for t in (lo, (lo + hi) // 2, hi):
        yy = py(t)
        text(draw, (left - 4, yy), f"{t}°", 13, anchor="rm")
        for gx in range(left, right, 6):
            draw.point((gx, yy), fill=BLACK)

    # rain bars (scaled: 2 mm/h fills 40 % of height)
    max_bar = (bottom - top) * 0.4
    for i, mm in enumerate(rain[:len(temps)]):
        if mm and mm > 0:
            bh = max(2, min(max_bar, mm / 2 * max_bar))
            bx = left + i * step
            draw.rectangle((bx - step / 2 + 1, bottom - bh, bx + step / 2 - 1, bottom), fill=BLACK)

    # temperature line (white halo keeps it visible on top of bars)
    pts = [(left + i * step, py(t)) for i, t in enumerate(temps)]
    draw.line(pts, fill=WHITE, width=6)
    draw.line(pts, fill=BLACK, width=3)

    # x axis: label every 6 h, thicker tick at midnight
    for i in range(len(temps)):
        t = t0 + timedelta(hours=i)
        if t.hour % 6 == 0:
            gx = left + i * step
            draw.line((gx, bottom, gx, bottom + (6 if t.hour == 0 else 3)), fill=BLACK)
            label = WD_SHORT[t.weekday()] if t.hour == 0 else f"{t.hour}"
            text(draw, (gx, bottom + 5), label, 13, bold=t.hour == 0, anchor="ma")
    draw.line((left, bottom, right, bottom), fill=BLACK)


def outlook(draw, box: Box, snap) -> None:
    x, y, w, h = box
    y = heading(draw, x, y, w, "Aussichten")
    stale_note(draw, x + w, box[1] + 2, snap)
    f = snap.value
    if f is None or not f.days:
        text(draw, (x, y + 10), "keine Daten", 22)
        return
    for d in f.days[1:6]:  # tomorrow + 4 days
        text(draw, (x, y), WD_SHORT[d.day.weekday()], 20, bold=True)
        temp = f"{num(d.t_min, 0)}/{num(d.t_max, 0)}°"
        text(draw, (x + 44, y), temp, 20)
        rain = num(d.precip_mm, 0 if (d.precip_mm or 0) >= 10 else 1, " mm") if (d.precip_mm or 0) >= 0.1 else ""
        text(draw, (x + w, y), rain, 18, anchor="ra")
        y += 28
