"""Google Calendar via private iCal URL (no OAuth, no extra libraries).

Handles: DTSTART as UTC (Z), local/TZID and all-day values, line folding,
and simple DAILY/WEEKLY recurrence without exceptions (kept deliberately small).
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from .. import net
from ..config import Config
from ..models import Event


def _unfold(text: str) -> list[str]:
    lines: list[str] = []
    for raw in text.replace("\r\n", "\n").split("\n"):
        if raw.startswith((" ", "\t")) and lines:
            lines[-1] += raw[1:]
        else:
            lines.append(raw)
    return lines


def _unescape(v: str) -> str:
    return v.replace("\\n", " ").replace("\\,", ",").replace("\\;", ";").replace("\\\\", "\\")


def _parse_dt(value: str, params: str, cfg: Config) -> tuple[datetime, bool]:
    """Return (aware datetime in cfg.tz, all_day)."""
    if "VALUE=DATE" in params or len(value) == 8:
        d = datetime.strptime(value[:8], "%Y%m%d")
        return d.replace(tzinfo=cfg.tz), True
    if value.endswith("Z"):
        d = datetime.strptime(value, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
        return d.astimezone(cfg.tz), False
    return datetime.strptime(value, "%Y%m%dT%H%M%S").replace(tzinfo=cfg.tz), False


def parse(text: str, cfg: Config, today: date) -> list[Event]:
    day_start = datetime.combine(today, datetime.min.time(), tzinfo=cfg.tz)
    day_end = day_start + timedelta(days=1)
    events: list[Event] = []
    cur: dict[str, tuple[str, str]] | None = None

    for line in _unfold(text):
        if line == "BEGIN:VEVENT":
            cur = {}
        elif line == "END:VEVENT" and cur is not None:
            ev = _to_event(cur, cfg, day_start, day_end)
            if ev:
                events.append(ev)
            cur = None
        elif cur is not None and ":" in line:
            head, _, value = line.partition(":")
            name, _, params = head.partition(";")
            cur[name] = (value, params)

    events.sort(key=lambda e: (e.start is not None, e.start or day_start))
    return events


def _to_event(props, cfg: Config, day_start: datetime, day_end: datetime) -> Event | None:
    if "DTSTART" not in props or props.get("STATUS", ("", ""))[0] == "CANCELLED":
        return None
    start, all_day = _parse_dt(*props["DTSTART"], cfg)
    if "DTEND" in props:
        end, _ = _parse_dt(*props["DTEND"], cfg)
    else:
        end = start + (timedelta(days=1) if all_day else timedelta())
    title = _unescape(props.get("SUMMARY", ("(ohne Titel)", ""))[0])

    rrule = props.get("RRULE", ("", ""))[0]
    if rrule:
        step = {"FREQ=DAILY": 1, "FREQ=WEEKLY": 7}.get(rrule.split(";")[0])
        if step and start < day_end:
            delta = end - start
            days = (day_start.date() - start.date()).days
            start += timedelta(days=(days // step) * step)
            end = start + delta
            if end <= day_start and not all_day:
                start += timedelta(days=step)
                end = start + delta

    overlaps = start < day_end and (end > day_start or start >= day_start)
    if not overlaps:
        return None
    return Event(None if all_day else start, title)


def fetch(cfg: Config) -> list[Event]:
    if not cfg.calendar_ics_url:
        raise ValueError("Calendar not configured")
    text = net.get(cfg.calendar_ics_url).decode("utf-8", errors="replace")
    return parse(text, cfg, datetime.now(cfg.tz).date())
