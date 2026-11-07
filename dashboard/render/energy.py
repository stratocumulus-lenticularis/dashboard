"""PV production and battery state."""

from __future__ import annotations

from .util import BLACK, NA, WHITE, heading, num, stale_note, text

Box = tuple[int, int, int, int]


def _kw(watt: float | None) -> str:
    return NA if watt is None else num(watt / 1000, 1, " kW")


def panel(draw, box: Box, snap) -> None:
    x, y, w, h = box
    y = heading(draw, x, y, w, "Solar & Batterie")
    stale_note(draw, x + w, box[1] + 2, snap)
    e = snap.value
    if e is None:
        text(draw, (x, y + 10), "keine Daten", 22)
        return

    text(draw, (x, y - 4), _kw(e.pv_w), 48, bold=True)
    text(draw, (x, y + 52), "Erzeugung", 16)

    # battery bar
    by = y + 76
    bar_w, bar_h = w - 70, 22
    draw.rectangle((x, by, x + bar_w, by + bar_h), outline=BLACK, width=2)
    if e.battery_soc is not None:
        fill = int((bar_w - 6) * max(0, min(100, e.battery_soc)) / 100)
        draw.rectangle((x + 3, by + 3, x + 3 + fill, by + bar_h - 3), fill=BLACK)
    text(draw, (x + w, by + bar_h // 2), num(e.battery_soc, 0, " %"), 22, bold=True, anchor="rm")

    if e.battery_w is None or abs(e.battery_w) < 20:
        state = "Batterie ruht"
    elif e.battery_w > 0:
        state = f"lädt mit {_kw(e.battery_w)}"
    else:
        state = f"entlädt mit {_kw(-e.battery_w)}"
    text(draw, (x, by + bar_h + 4), state, 16)

    ry = by + bar_h + 28
    text(draw, (x, ry), "Verbrauch", 16)
    text(draw, (x + w, ry), _kw(e.consumption_w), 16, bold=True, anchor="ra")
    if e.grid_w is not None:
        label = "Netzbezug" if e.grid_w >= 0 else "Einspeisung"
        text(draw, (x, ry + 22), label, 16)
        text(draw, (x + w, ry + 22), _kw(abs(e.grid_w)), 16, bold=True, anchor="ra")
