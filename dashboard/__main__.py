"""Entry point: python -m dashboard [--once] [--demo]"""

from __future__ import annotations

import argparse
import logging
from datetime import datetime

from .config import load_config


def main() -> None:
    ap = argparse.ArgumentParser(prog="dashboard")
    ap.add_argument("--once", action="store_true", help="update once and exit")
    ap.add_argument("--demo", action="store_true", help="render sample data (no APIs)")
    args = ap.parse_args()

    cfg = load_config()
    logging.basicConfig(
        level=getattr(logging, cfg.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

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
