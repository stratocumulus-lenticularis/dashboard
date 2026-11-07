"""Clock-aligned refresh loop with nightly sleep mode."""

from __future__ import annotations

import logging
import time as _time
from datetime import datetime, time, timedelta

from .config import Config
from .hub import Hub
from .render import compose

log = logging.getLogger(__name__)


def in_sleep_window(now: datetime, start: time, end: time) -> bool:
    t = now.time()
    if start <= end:
        return start <= t < end
    return t >= start or t < end  # window wraps over midnight


def next_slot(now: datetime, minutes: int) -> datetime:
    """Next wall-clock multiple of `minutes` (e.g. :00 and :30)."""
    base = now.replace(minute=0, second=0, microsecond=0)
    slot = base
    while slot <= now:
        slot += timedelta(minutes=minutes)
    return slot


def next_wake(now: datetime, end: time) -> datetime:
    wake = datetime.combine(now.date(), end, tzinfo=now.tzinfo)
    return wake if wake > now else wake + timedelta(days=1)


def wait_for_clock(cfg: Config, max_wait: int = 120) -> None:
    """After boot the Pi may not have NTP time yet (no RTC). Wait briefly."""
    for _ in range(max_wait // 5):
        if datetime.now(cfg.tz).year >= 2024:
            return
        _time.sleep(5)


def sleep_until(target: datetime, cfg: Config) -> None:
    while True:
        remaining = (target - datetime.now(cfg.tz)).total_seconds()
        if remaining <= 0:
            return
        _time.sleep(min(remaining, 60))  # short naps survive clock jumps (NTP)


def run(cfg: Config, display, once: bool = False) -> None:
    hub = Hub(cfg)
    wait_for_clock(cfg)
    asleep = False
    while True:
        now = datetime.now(cfg.tz)
        if in_sleep_window(now, cfg.sleep_start, cfg.sleep_end):
            if not asleep:
                log.info("entering sleep mode")
                display.show(compose.render_sleep(now, cfg.sleep_end.strftime("%H:%M")))
                asleep = True
            if once:
                return
            sleep_until(next_wake(now, cfg.sleep_end), cfg)
            continue

        if asleep:  # first frame after the night: clear to remove ghosting
            display.clear()
            asleep = False

        try:
            data = hub.refresh()
            frame = compose.render(data, datetime.now(cfg.tz))
            display.show(frame)
            log.info("display updated")
        except Exception:  # noqa: BLE001 - keep running for months
            log.exception("update cycle failed")
        if once:
            return
        sleep_until(next_slot(datetime.now(cfg.tz), cfg.refresh_minutes), cfg)
