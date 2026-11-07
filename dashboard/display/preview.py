"""Development display: writes the frame to a PNG file."""

from __future__ import annotations

import logging
from pathlib import Path

from PIL import Image

log = logging.getLogger(__name__)


class PreviewDisplay:
    def __init__(self, path: Path) -> None:
        self.path = path

    def show(self, image: Image.Image) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        image.save(self.path)
        log.info("preview written to %s", self.path)

    def clear(self) -> None:
        pass
