import logging
from datetime import datetime, timezone, time as dtime
from typing import Dict, Optional

import requests
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from ..utils.cache import DataCache

TeamLogoInfo = Dict[str, str]


class NFLService:
    """Lightweight ESPN-backed schedule fetcher for a single NFL team."""

    def __init__(
        self,
        team_id: int = 11,
        team_abbr: str = "IND",
        team_name: str = "Colts",
        team_timezone: str = "America/Chicago",
        schedule_source_tz: str = "America/New_York",
        cache_ttl_seconds: int = 900,
        cache: Optional[DataCache] = None,
    ):
        self.team_id = team_id
        self.team_abbr = team_abbr
        self.team_name = team_name
        self.team_timezone = team_timezone
        self.schedule_source_tz = schedule_source_tz
        self.logger = logging.getLogger(__name__)
        self.schedule_url = (
            f"https://site.web.api.espn.com/apis/v2/sports/football/nfl/teams/{team_id}/schedule"
        )
        self.cache = cache or DataCache(logger=self.logger)
        self.cache_ttl_seconds = max(cache_ttl_seconds, 120)

    def _resolve_tz(self, tz_name: str) -> Optional[ZoneInfo]:
        alias_map = {
            "america/chicago": "US/Central",
            "america/new_york": "US/Eastern",
            "america/denver": "US/Mountain",
            "america/los_angeles": "US/Pacific",
        }
        tz_candidates = [tz_name, alias_map.get(tz_name.lower()) if tz_name else None]
        for tz_name in (tz for tz in tz_candidates if tz):
            try:
                return ZoneInfo(tz_name)
            except ZoneInfoNotFoundError:
                continue

        # Fall back to dateutil if tzdata is missing in the runtime
        try:
            from dateutil import tz  # type: ignore

            for tz_name in (tz for tz in tz_candidates if tz):
                candidate = tz.gettz(tz_name)
                if candidate:
                    return candidate
        except Exception:
            pass

        return None

    def _get_tz(self) -> Optional[ZoneInfo]:
        resolved = self._resolve_tz(self.team_timezone)
        if resolved:
            return resolved
        self.logger.warning("Timezone %s unavailable; using UTC", self.team_timezone)
        return timezone.utc

    def _get_source_tz(self) -> Optional[ZoneInfo]:
        resolved = self._resolve_tz(self.schedule_source_tz)
        if not resolved:
            self.logger.warning(
                "Schedule source timezone %s unavailable; using UTC",
                self.schedule_source_tz,
            )
            return timezone.utc
        return resolved

    def get_next_game(self) -> Optional[Dict[str, str]]:
        """Return opponent and kickoff info for the next upcoming game."""
        return self.cache.get(
            f"nfl:next_game:{self.team_id}",
            self._get_next_game_uncached,
            ttl_seconds=self.cache_ttl_seconds,
            allow_stale=True,
        )

    def _get_next_game_uncached(self):
        game = self._fetch_espn_next_game()
        if game:
            return game
        self.logger.warning("ESPN schedule unavailable; trying nfl_data_py fallback.")
        return self._fetch_next_game_nfl_data_py()

    def _fetch_espn_next_game(self) -> Optional[Dict[str, str]]:
        try:
            resp = requests.get(self.schedule_url, timeout=10)
            resp.raise_for_status()
        except requests.HTTPError as exc:
            status = exc.response.status_code if exc.response else None
            self.logger.warning(
                "Failed to fetch NFL schedule (status %s); using fallback", status or "unknown"
            )
            return None
        except requests.RequestException as exc:
            self.logger.warning("Failed to fetch NFL schedule: %s", exc)
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
            opponent_nickname = opponent.get("team", {}).get("nickname") or opponent_name
            opponent_id = opponent.get("id") or opponent.get("team", {}).get("id")

            date_raw = event.get("date")
            kickoff_local = None
            kickoff_str = "TBD"
            if date_raw:
                try:
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
                "opponent_nickname": opponent_nickname,
                "opponent_id": str(opponent_id) if opponent_id else "",
            }
        return None

    def _fetch_next_game_nfl_data_py(self) -> Optional[Dict[str, str]]:
        """Fallback using nfl_data_py schedules if ESPN is unavailable."""
        try:
            import nfl_data_py as ndp  # type: ignore
            import pandas as pd  # type: ignore
        except Exception as exc:
            self.logger.error("nfl_data_py not available: %s", exc)
            return None

        try:
            current_year = datetime.now().year
            schedules = ndp.import_schedules([current_year])
        except Exception as exc:
            self.logger.error("Failed to import schedules from nfl_data_py: %s", exc)
            return None

        try:
            teams = ndp.import_team_desc()
            nick_lookup = {
                str(row.get("team_id") or "").lower(): row.get("team_nickname") or row.get("team_name") or ""
                for _idx, row in teams.iterrows()
            }
            abbr_lookup = {
                (row.get("team_id") or "").lower(): row.get("team_abbr") or ""
                for _idx, row in teams.iterrows()
            }
            name_lookup = {
                (row.get("team_id") or "").lower(): row.get("team_name") or ""
                for _idx, row in teams.iterrows()
            }
        except Exception:
            nick_lookup = {}
            abbr_lookup = {}
            name_lookup = {}

        try:
            df = schedules
            df = df[
                (df["home_team"] == self.team_abbr)
                | (df["away_team"] == self.team_abbr)
            ]
            df = df.copy()
            df["game_date"] = pd.to_datetime(df["gameday"], errors="coerce").dt.tz_localize(None)
            now = pd.Timestamp.utcnow().tz_localize(None)
            upcoming = df[df["game_date"] >= now]
            if upcoming.empty:
                upcoming = df
            upcoming = upcoming.sort_values("game_date")
            next_game = upcoming.iloc[0].to_dict()
        except Exception as exc:
            self.logger.error("Failed to select next game from nfl_data_py data: %s", exc)
            return None

        is_home = next_game.get("home_team") == self.team_abbr
        opponent_abbr = next_game.get("away_team") if is_home else next_game.get("home_team")
        opponent_abbr = str(opponent_abbr or "").upper()
        opponent_id = str(next_game.get("away_team_id") if is_home else next_game.get("home_team_id") or "").lower()
        opponent_name = name_lookup.get(opponent_id, opponent_abbr) if opponent_id else opponent_abbr
        opponent_nickname = nick_lookup.get(opponent_id, opponent_name)

        kickoff_dt = next_game.get("game_date")
        gametime_raw = next_game.get("gametime") or next_game.get("game_time") or next_game.get(
            "start_time"
        )
        kickoff_str = "TBD"
        tzinfo = self._get_tz()
        source_tz = self._get_source_tz()
        try:
            if pd.notnull(kickoff_dt):
                kickoff_dt = kickoff_dt.to_pydatetime()
                if gametime_raw:
                    try:
                        parsed_time = pd.to_datetime(str(gametime_raw)).time()
                        kickoff_dt = datetime.combine(kickoff_dt.date(), parsed_time)
                    except Exception:
                        pass
                elif kickoff_dt.hour == 0 and kickoff_dt.minute == 0:
                    # Schedules without time default to midnight; assume noon local instead.
                    kickoff_dt = datetime.combine(kickoff_dt.date(), dtime(hour=12))
                if kickoff_dt.tzinfo is None:
                    kickoff_dt = kickoff_dt.replace(tzinfo=source_tz or timezone.utc)
                if tzinfo:
                    kickoff_dt = kickoff_dt.astimezone(tzinfo)
                kickoff_str = kickoff_dt.strftime("%a %I:%M %p %Z").lstrip("0")
        except Exception:
            kickoff_str = "TBD"

        venue = next_game.get("site") or ""

        return {
            "opponent_abbr": opponent_abbr,
            "opponent_name": opponent_name,
            "home": bool(is_home),
            "kickoff": kickoff_str,
            "venue": venue,
            "opponent_nickname": opponent_nickname,
            "opponent_id": opponent_id,
        }
