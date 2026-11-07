"""Waveshare 7.5" V2 (800x480, B/W) driver wrapper.

The vendor library is NOT part of this repo (see docs/DEPLOYMENT.md). It is
looked up as `waveshare_epd`, optionally from WAVESHARE_LIB_DIR.

Every update does init -> display -> sleep, so the panel is never left
powered (protects the e-paper and saves power during the 30 min wait).
"""

from __future__ import annotations

import logging
import os
import sys

from PIL import Image

log = logging.getLogger(__name__)


class WaveshareDisplay:
    def __init__(self) -> None:
        lib = os.environ.get("WAVESHARE_LIB_DIR")
        if lib and lib not in sys.path:
            sys.path.append(lib)
        from waveshare_epd import epd7in5_V2  # ImportError -> caller falls back

        self._epd = epd7in5_V2.EPD()

    def show(self, image: Image.Image) -> None:
        epd = self._epd
        try:
            epd.init()  # full waveform: best contrast, no ghosting
            epd.display(epd.getbuffer(image.convert("1")))
        finally:
            epd.sleep()

    def clear(self) -> None:
        epd = self._epd
        try:
            epd.init()
            epd.Clear()
        finally:
            epd.sleep()
