import logging
from datetime import datetime
from typing import Dict, Optional

import requests
from zoneinfo import ZoneInfo


class NFLService:
    """Lightweight ESPN-backed schedule fetcher for a single NFL team."""

    def __init__(
        self,
        team_id: int = 11,
        team_abbr: str = "IND",
        team_name: str = "Colts",
        team_timezone: str = "America/Chicago",
    ):
        self.team_id = team_id
        self.team_abbr = team_abbr
        self.team_name = team_name
        self.team_timezone = team_timezone
        self.logger = logging.getLogger(__name__)
        self.schedule_url = (
            f"https://site.api.espn.com/apis/v2/sports/football/nfl/teams/{team_id}/schedule"
        )

    def _get_tz(self) -> Optional[ZoneInfo]:
        try:
            return ZoneInfo(self.team_timezone)
        except Exception:
            self.logger.warning("Invalid timezone %s; using UTC", self.team_timezone)
            return None

    def get_next_game(self) -> Optional[Dict[str, str]]:
        """Return opponent and kickoff info for the next upcoming game."""
        try:
            resp = requests.get(self.schedule_url, timeout=10)
            resp.raise_for_status()
        except requests.RequestException as exc:
            self.logger.error("Failed to fetch NFL schedule: %s", exc)
            return None

        payload = resp.json()
        events = payload.get("events") or []
        tzinfo = self._get_tz()

        for event in events:
            status = event.get("status", {})
            state = (status.get("type") or {}).get("state", "").lower()
            if state == "post":
                continue

            competitors = (
                event.get("competitions", [{}])[0].get("competitors") or []
            )
            if len(competitors) != 2:
                continue

            # Identify opponent relative to our team id
            opponent = None
            is_home = None
            for comp in competitors:
                if str(comp.get("id")) == str(self.team_id):
                    is_home = (comp.get("homeAway") or "").lower() == "home"
                else:
                    opponent = comp

            if not opponent:
                continue

            opponent_abbr = opponent.get("abbreviation") or opponent.get("team", {}).get(
                "abbreviation", "OPP"
            )
            opponent_name = opponent.get("displayName") or opponent.get(
                "team", {}
            ).get("displayName", "Opponent")

            date_raw = event.get("date")
            kickoff_local = None
            kickoff_str = "TBD"
            if date_raw:
                try:
                    # date_raw is ISO8601; enforce tz then convert
                    kickoff_dt = datetime.fromisoformat(date_raw.replace("Z", "+00:00"))
                    if tzinfo:
                        kickoff_local = kickoff_dt.astimezone(tzinfo)
                        kickoff_str = kickoff_local.strftime("%a %I:%M %p").lstrip("0")
                    else:
                        kickoff_str = kickoff_dt.strftime("%a %I:%M %p UTC").lstrip("0")
                except Exception:
                    kickoff_str = "TBD"

            venue = (event.get("competitions", [{}])[0].get("venue") or {}).get(
                "fullName"
            )
            return {
                "opponent_abbr": opponent_abbr,
                "opponent_name": opponent_name,
                "home": bool(is_home),
                "kickoff": kickoff_str,
                "venue": venue or "",
            }
        return None
