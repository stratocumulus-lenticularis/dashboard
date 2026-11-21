"""Google Calendar via the private iCal address (no OAuth, stdlib only).

Supported (what Google exports):
- DTSTART/DTEND as UTC (Z), with TZID, floating, and all-day (VALUE=DATE)
- RRULE FREQ=DAILY/WEEKLY/MONTHLY/YEARLY with INTERVAL, COUNT, UNTIL, BYDAY
  (weekly) - enough for typical family calendars
- EXDATE (deleted single occurrences) and RECURRENCE-ID (moved/changed single
  occurrences), STATUS:CANCELLED
Not supported: BYSETPOS, "last Friday of the month" style rules, RDATE.
Such events are shown on their first date only.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from .. import net
from ..config import Config
from ..models import Event

log = logging.getLogger(__name__)

WEEKDAYS = {"MO": 0, "TU": 1, "WE": 2, "TH": 3, "FR": 4, "SA": 5, "SU": 6}
MAX_OCCURRENCES = 5000  # safety limit for COUNT-less endless rules


@dataclass
class _Raw:
    props: dict[str, list[tuple[dict[str, str], str]]] = field(default_factory=dict)

    def first(self, name: str) -> tuple[dict[str, str], str] | None:
        v = self.props.get(name)
        return v[0] if v else None


def _unfold(text: str) -> list[str]:
    lines: list[str] = []
    for raw in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        if raw[:1] in (" ", "\t") and lines:
            lines[-1] += raw[1:]
        else:
            lines.append(raw)
    return lines


def _unescape(v: str) -> str:
    return (v.replace("\\n", " ").replace("\\N", " ").replace("\\,", ",")
            .replace("\\;", ";").replace("\\\\", "\\"))


def _split_params(head: str) -> tuple[str, dict[str, str]]:
    name, *rest = head.split(";")
    params = {}
    for item in rest:
        k, _, v = item.partition("=")
        params[k.upper()] = v.strip('"')
    return name.upper(), params


def _events(text: str) -> list[_Raw]:
    out: list[_Raw] = []
    cur: _Raw | None = None
    for line in _unfold(text):
        if line == "BEGIN:VEVENT":
            cur = _Raw()
        elif line == "END:VEVENT":
            if cur is not None:
                out.append(cur)
            cur = None
        elif cur is not None and ":" in line:
            head, _, value = line.partition(":")
            name, params = _split_params(head)
            cur.props.setdefault(name, []).append((params, value))
    return out


def _dt(params: dict[str, str], value: str, tz: ZoneInfo) -> tuple[datetime, bool]:
    """-> (aware datetime in `tz`, all_day)."""
    value = value.strip()
    if params.get("VALUE") == "DATE" or len(value) == 8:
        return datetime.strptime(value[:8], "%Y%m%d").replace(tzinfo=tz), True
    if value.endswith("Z"):
        d = datetime.strptime(value, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
        return d.astimezone(tz), False
    src = tz
    if params.get("TZID"):
        try:
            src = ZoneInfo(params["TZID"])
        except Exception:  # noqa: BLE001 - unknown zone name: assume local
            log.debug("unknown TZID %r", params["TZID"])
    return datetime.strptime(value, "%Y%m%dT%H%M%S").replace(tzinfo=src).astimezone(tz), False


def _rrule(value: str) -> dict[str, str]:
    return dict(p.split("=", 1) for p in value.split(";") if "=" in p)


def _add_months(d: datetime, months: int) -> datetime | None:
    """Same day-of-month `months` later, or None if that day does not exist."""
    y, m = divmod(d.year * 12 + d.month - 1 + months, 12)
    try:
        return d.replace(year=y, month=m + 1)
    except ValueError:  # e.g. 31st in a 30-day month: iCal skips such dates
        return None


def _occurrences(start: datetime, rule: dict[str, str], tz: ZoneInfo, until_day: date):
    """Yield start datetimes of a recurring event up to and including `until_day`."""
    freq = rule.get("FREQ", "")
    interval = max(1, int(rule.get("INTERVAL", "1") or 1))
    count = int(rule["COUNT"]) if rule.get("COUNT", "").isdigit() else None
    limit = until_day
    if rule.get("UNTIL"):
        u, _ = _dt({}, rule["UNTIL"], tz)
        limit = min(limit, u.date())

    produced = 0
    if freq == "WEEKLY":
        days = sorted(WEEKDAYS[d[-2:]] for d in rule.get("BYDAY", "").split(",") if d[-2:] in WEEKDAYS)
        days = days or [start.weekday()]
        week0 = start.date() - timedelta(days=start.weekday())
        n = 0
        while produced < MAX_OCCURRENCES:
            base = week0 + timedelta(weeks=n * interval)
            if base > limit:
                return
            for wd in days:
                d = base + timedelta(days=wd)
                if d < start.date():
                    continue
                if d > limit or (count is not None and produced >= count):
                    return
                produced += 1
                yield datetime.combine(d, start.timetz().replace(tzinfo=None), tzinfo=tz)
            n += 1
        return

    step = {"DAILY": lambda i: start + timedelta(days=i * interval),
            "MONTHLY": lambda i: _add_months(start, i * interval),
            "YEARLY": lambda i: _add_months(start, i * interval * 12)}.get(freq)
    if step is None:
        yield start
        return
    i = 0
    while i < MAX_OCCURRENCES:
        occ = step(i)
        i += 1
        if occ is None:  # skipped, non-existing date; it still counts as a step
            continue
        if occ.date() > limit or (count is not None and produced >= count):
            return
        produced += 1
        yield datetime.combine(occ.date(), start.timetz().replace(tzinfo=None), tzinfo=tz)


def parse(text: str, cfg: Config, today: date) -> list[Event]:
    """All events of `today`, sorted: all-day first, then by start time."""
    tz = cfg.tz
    day_start = datetime.combine(today, time.min, tzinfo=tz)
    day_end = day_start + timedelta(days=1)

    raws = _events(text)
    # single changed occurrences replace the generated one: (UID, original start)
    overrides = {}
    for r in raws:
        rid, uid = r.first("RECURRENCE-ID"), r.first("UID")
        if rid and uid:
            overrides[(uid[1], _dt(*rid, tz)[0])] = r

    events: list[Event] = []

    def add(raw: _Raw, start: datetime, all_day: bool, length: timedelta) -> None:
        if raw.first("STATUS") and raw.first("STATUS")[1].upper() == "CANCELLED":
            return
        end = start + length
        # all-day: [start, end); timed: also show zero-length events starting today
        if start < day_end and (end > day_start or (end == start and start >= day_start)):
            title = _unescape(raw.first("SUMMARY")[1]) if raw.first("SUMMARY") else "(ohne Titel)"
            events.append(Event(None if all_day else start, title))

    for r in raws:
        ds = r.first("DTSTART")
        if not ds:
            continue
        start, all_day = _dt(*ds, tz)
        de = r.first("DTEND")
        if de:
            length = _dt(*de, tz)[0] - start
        else:
            length = timedelta(days=1) if all_day else timedelta()
        uid = r.first("UID")

        if r.first("RECURRENCE-ID"):  # a moved/changed occurrence: used as is
            add(r, start, all_day, length)
            continue
        rrule = r.first("RRULE")
        if not rrule:
            add(r, start, all_day, length)
            continue

        excluded = set()
        for params, value in r.props.get("EXDATE", []):
            for v in value.split(","):
                excluded.add(_dt(params, v, tz)[0])
        # an occurrence that begins earlier can still reach into today
        lookback = max(length, timedelta())
        for occ in _occurrences(start, _rrule(rrule[1]), tz, today):
            if occ in excluded or (uid and (uid[1], occ) in overrides):
                continue
            if occ + lookback < day_start:
                continue
            add(r, occ, all_day, length)

    events.sort(key=lambda e: (e.start is not None, e.start or day_start, e.title))
    return events


def _urls(cfg: Config) -> list[str]:
    return cfg.calendar_ics_url.split()


def fetch(cfg: Config) -> list[Event]:
    urls = _urls(cfg)
    if not urls:
        raise ValueError("Calendar not configured")
    today = datetime.now(cfg.tz).date()
    events: list[Event] = []
    failed = 0
    for url in urls:
        try:
            text = net.get(url).decode("utf-8", errors="replace")
            events += parse(text, cfg, today)
        except Exception as exc:  # noqa: BLE001 - one broken calendar must not hide the others
            failed += 1
            # never log the URL itself: it is a secret
            log.warning("calendar %d/%d failed: %s: %s", urls.index(url) + 1, len(urls),
                        type(exc).__name__, getattr(exc, "reason", exc))
    if failed == len(urls):
        raise RuntimeError("all calendars failed")
    events.sort(key=lambda e: (e.start is not None, e.start or datetime.min.replace(tzinfo=cfg.tz), e.title))
    return events

