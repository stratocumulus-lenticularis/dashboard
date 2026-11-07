"""Next Arsenal match from football-data.org (free tier, token required)."""

from __future__ import annotations

from datetime import datetime, timezone

from .. import net
from ..config import Config
from ..models import Match

URL = "https://api.football-data.org/v4/teams/{team}/matches?status=SCHEDULED,TIMED"


def parse(data: dict, cfg: Config) -> Match | None:
    matches = data.get("matches", [])
    if not matches:
        return None
    m = min(matches, key=lambda x: x["utcDate"])
    kickoff = datetime.strptime(m["utcDate"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    name = lambda t: t.get("shortName") or t.get("name") or "?"  # noqa: E731
    return Match(
        kickoff=kickoff.astimezone(cfg.tz),
        home=name(m["homeTeam"]),
        away=name(m["awayTeam"]),
        competition=m.get("competition", {}).get("name", ""),
    )


def fetch(cfg: Config) -> Match | None:
    if not cfg.football_token:
        raise ValueError("Football data token not configured")
    data = net.get_json(
        URL.format(team=cfg.arsenal_team_id), {"X-Auth-Token": cfg.football_token}
    )
    return parse(data, cfg)
