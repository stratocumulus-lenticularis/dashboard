"""Display drivers. Choose with DISPLAY_DRIVER=auto|waveshare|preview."""

from __future__ import annotations

import logging

from ..config import Config

log = logging.getLogger(__name__)


def get_display(cfg: Config):
    choice = cfg.display_driver.lower()
    if choice in ("waveshare", "auto"):
        try:
            from .waveshare import WaveshareDisplay

            return WaveshareDisplay()
        except Exception as exc:  # noqa: BLE001
            if choice == "waveshare":
                raise
            log.info("Waveshare driver unavailable (%s) - using PNG preview", exc)
    from .preview import PreviewDisplay

    return PreviewDisplay(cfg.data_dir / "preview.png")
