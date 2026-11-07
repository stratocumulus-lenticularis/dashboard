"""Font loading with cache. DejaVu ships with Raspberry Pi OS (fonts-dejavu-core)."""

from __future__ import annotations

import os
from functools import lru_cache

from PIL import ImageFont

_CANDIDATES = {
    False: [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "C:/Windows/Fonts/arial.ttf",
        "DejaVuSans.ttf",
    ],
    True: [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
        "DejaVuSans-Bold.ttf",
    ],
}


@lru_cache(maxsize=32)
def font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    override = os.environ.get("FONT_BOLD" if bold else "FONT_REGULAR")
    for path in ([override] if override else []) + _CANDIDATES[bold]:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()
