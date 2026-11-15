"""Entry point: python -m dashboard [--once] [--demo] [--check]"""

from __future__ import annotations

import argparse
import logging
from datetime import datetime

from .config import load_config


def main() -> None:
    ap = argparse.ArgumentParser(prog="dashboard")
    ap.add_argument("--once", action="store_true", help="update once and exit")
    ap.add_argument("--demo", action="store_true", help="render sample data (no APIs)")
    ap.add_argument("--check", action="store_true", help="fetch all sources and print diagnostics")
    args = ap.parse_args()

    cfg = load_config()
    logging.basicConfig(
        level=getattr(logging, cfg.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    if args.check:  # no display access needed
        from .check import run as run_check

        run_check(cfg)
        return

    from .display import get_display

    display = get_display(cfg)

    if args.demo:
        from .demo import sample
        from .render.compose import render

        now = datetime.now(cfg.tz)
        display.show(render(sample(now), now))
        return

    from .scheduler import run

    run(cfg, display, once=args.once)


if __name__ == "__main__":
    main()
