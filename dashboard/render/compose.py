"""Page composition: 800x480 landscape, 1-bit.

    +----------------------------------------------+ 0
    | header: date                        Stand    |
    +-------------+-------------+------------------+ 40
    | Draussen    | Solar       | Heute            |
    +-------------+-------------+------------------+ 212
    | Prognose 48h chart        | Aussichten       |
    +---------------------------+------------------+ 424
    | Arsenal countdown                            |
    +----------------------------------------------+ 480
"""

from __future__ import annotations

import logging
from datetime import datetime

from PIL import Image, ImageDraw

from ..config import HEIGHT, WIDTH
from . import calendar, energy, weather
from .util import BLACK, WHITE, long_date, text

log = logging.getLogger(__name__)

M = 10  # outer margin
HEADER_H = 40
FOOTER_Y = 432
MID_Y = 232
COL1, COL2 = 250, 520  # vertical column rules (top row)
CHART_W = 540  # chart / outlook split (bottom row)


def _safe(name: str, fn, *args) -> None:
    """A crashing panel must not take the whole screen down."""
    try:
        fn(*args)
    except Exception:  # noqa: BLE001
        log.exception("panel %s failed", name)


def render(data: dict, now: datetime) -> Image.Image:
    img = Image.new("1", (WIDTH, HEIGHT), WHITE)
    d = ImageDraw.Draw(img)

    # header
    text(d, (M, 6), long_date(now), 26, bold=True)
    text(d, (WIDTH - M, 14), now.strftime("%H:%M"), 20, anchor="ra")
    d.line((0, HEADER_H, WIDTH, HEADER_H), fill=BLACK, width=2)

    # rules
    for vx in (COL1, COL2):
        d.line((vx, HEADER_H, vx, MID_Y), fill=BLACK)
    d.line((0, MID_Y, WIDTH, MID_Y), fill=BLACK)
    d.line((CHART_W, MID_Y, CHART_W, FOOTER_Y), fill=BLACK)
    d.line((0, FOOTER_Y, WIDTH, FOOTER_Y), fill=BLACK, width=2)

    top_h = MID_Y - HEADER_H - 6
    _safe("current", weather.current, d, (M, HEADER_H + 6, COL1 - 2 * M, top_h), data["observation"])
    _safe("energy", energy.panel, d, (COL1 + M, HEADER_H + 6, COL2 - COL1 - 2 * M, top_h), data["energy"])
    _safe("calendar", calendar.today, d, (COL2 + M, HEADER_H + 6, WIDTH - COL2 - 2 * M, top_h), data["calendar"])

    bot_h = FOOTER_Y - MID_Y - 6
    _safe("chart", weather.chart, d, (M, MID_Y + 6, CHART_W - 2 * M, bot_h), data["forecast"], now)
    _safe("outlook", weather.outlook, d, (CHART_W + M, MID_Y + 6, WIDTH - CHART_W - 2 * M, bot_h), data["forecast"])

    _safe("arsenal", calendar.arsenal, d, (M, FOOTER_Y + 2, WIDTH - 2 * M, HEIGHT - FOOTER_Y - 4), data["match"], now)
    return img


def render_sleep(now: datetime, wake: str) -> Image.Image:
    """Static screen shown during the night (no updates until `wake`)."""
    img = Image.new("1", (WIDTH, HEIGHT), WHITE)
    d = ImageDraw.Draw(img)
    text(d, (WIDTH // 2, HEIGHT // 2 - 30), "Ruhemodus", 56, bold=True, anchor="mm")
    text(d, (WIDTH // 2, HEIGHT // 2 + 30), f"Aktualisierung wieder ab {wake} Uhr", 24, anchor="mm")
    return img
