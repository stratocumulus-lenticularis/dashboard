"""Drawing helpers and German formatting (no locale dependency)."""

from __future__ import annotations

from datetime import datetime

from PIL import ImageDraw

from .fonts import font

BLACK, WHITE = 0, 255

WEEKDAYS = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]
WD_SHORT = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]
MONTHS = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli",
          "August", "September", "Oktober", "November", "Dezember"]

NA = "–"


def num(v: float | None, digits: int = 0, unit: str = "") -> str:
    """Number with decimal point, '–' if missing."""
    if v is None:
        return NA
    s = f"{v:.{digits}f}"  # decimal point (not comma), as requested
    if s.startswith("-0") and float(v) > -0.5 * 10 ** -digits:
        s = s[1:]
    return s + unit


def long_date(d: datetime) -> str:
    return f"{WEEKDAYS[d.weekday()]}, {d.day}. {MONTHS[d.month - 1]} {d.year}"


def text_w(draw: ImageDraw.ImageDraw, s: str, size: int, bold: bool = False) -> int:
    return int(draw.textlength(s, font=font(size, bold)))


def text(draw, xy, s: str, size: int, bold: bool = False, anchor: str = "la") -> None:
    draw.text(xy, s, font=font(size, bold), fill=BLACK, anchor=anchor)


def fit(draw, s: str, size: int, max_w: int, bold: bool = False) -> str:
    """Shorten with an ellipsis so that s fits into max_w pixels."""
    if text_w(draw, s, size, bold) <= max_w:
        return s
    while s and text_w(draw, s + "…", size, bold) > max_w:
        s = s[:-1]
    return s.rstrip() + "…"


def heading(draw, x: int, y: int, w: int, title: str) -> int:
    """Small bold section title with a rule below. Returns y below the rule."""
    text(draw, (x, y), title.upper(), 15, bold=True)
    draw.line((x, y + 20, x + w, y + 20), fill=BLACK, width=1)
    return y + 26


def stale_note(draw, x: int, y: int, snap, anchor: str = "ra") -> None:
    """Mark outdated data: 'Stand HH:MM' (or 'keine Daten')."""
    if not snap.stale:
        return
    label = "Stand " + snap.fetched_at.strftime("%H:%M") if snap.fetched_at else "keine Daten"
    text(draw, (x, y), label, 13, anchor=anchor)
