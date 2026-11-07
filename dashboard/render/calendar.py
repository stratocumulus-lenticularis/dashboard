"""Today's calendar entries and the Arsenal countdown."""

from __future__ import annotations

from datetime import datetime

from .util import BLACK, WD_SHORT, fit, heading, stale_note, text, text_w

Box = tuple[int, int, int, int]


def today(draw, box: Box, snap) -> None:
    x, y, w, h = box
    y = heading(draw, x, y, w, "Heute")
    stale_note(draw, x + w, box[1] + 2, snap)
    events = snap.value
    if events is None:
        text(draw, (x, y + 10), "keine Daten", 22)
        return
    if not events:
        text(draw, (x, y + 10), "Keine Termine", 22)
        return
    row_h = 26
    max_rows = max(1, (box[1] + h - y) // row_h)
    shown = events[:max_rows]
    if len(events) > max_rows:  # reserve last row for the overflow hint
        shown = events[:max_rows - 1]
    for ev in shown:
        when = ev.start.strftime("%H:%M") if ev.start else "ganztägig"
        tw = 62 if ev.start else 0
        if ev.start:
            text(draw, (x, y), when, 19, bold=True)
        title = fit(draw, ev.title, 19, w - tw - (0 if ev.start else 0))
        text(draw, (x + tw, y), title, 19)
        y += row_h
    if len(events) > len(shown):
        text(draw, (x, y), f"+ {len(events) - len(shown)} weitere", 16)


def _countdown(delta_days: int, delta_hours: int) -> str:
    if delta_days <= 0:
        return f"in {max(delta_hours, 0)} Std."
    if delta_days == 1:
        return "morgen"
    return f"in {delta_days} Tagen"


def arsenal(draw, box: Box, snap, now: datetime) -> None:
    x, y, w, h = box
    mid = y + h // 2
    m = snap.value
    if m is None:
        label = "Arsenal: keine Daten" if snap.stale else "Arsenal: kein Spiel angesetzt"
        text(draw, (x, mid), label, 22, anchor="lm")
        return
    secs = (m.kickoff - now).total_seconds()
    days = m.kickoff.date().toordinal() - now.date().toordinal()
    count = _countdown(days, int(secs // 3600))
    when = f"{WD_SHORT[m.kickoff.weekday()]} {m.kickoff.strftime('%d.%m. %H:%M')}"
    right = text_w(draw, count, 28, True)
    title = fit(draw, f"{m.home} – {m.away}", 24, w - right - 200, bold=True)
    text(draw, (x, mid), title, 24, bold=True, anchor="lm")
    text(draw, (x + w - right - 16, mid), when, 20, anchor="rm")
    text(draw, (x + w, mid), count, 28, bold=True, anchor="rm")
