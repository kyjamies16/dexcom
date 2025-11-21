import logging
from pathlib import Path
from typing import Optional

from PIL import Image

from ..matrix.helper import graphics
from ..services.nfl import NFLService
from .base import BaseDisplay


LOGO_ABBR_ALIASES = {
    "ari": ["cardinals", "arizona"],
    "atl": ["falcons", "atlanta"],
    "bal": ["ravens", "baltimore"],
    "buf": ["bills", "buffalo"],
    "car": ["panthers", "carolina"],
    "chi": ["bears", "chicago"],
    "cin": ["bengals", "cincinnati"],
    "cle": ["browns", "cleveland"],
    "dal": ["cowboys", "dallas"],
    "den": ["broncos", "denver"],
    "det": ["lions", "detroit"],
    "gb": ["packers", "greenbay", "green_bay"],
    "hou": ["texans", "houston"],
    "ind": ["colts", "indianapolis"],
    "jax": ["jaguars", "jacksonville"],
    "kc": ["chiefs", "kansascity", "kansas_city", "kansas-city"],
    "lv": ["raiders", "lasvegas", "las_vegas"],
    "lac": ["chargers", "losangeles", "los_angeles"],
    "lar": ["rams", "losangeles", "los_angeles"],
    "mia": ["dolphins", "miami"],
    "min": ["vikings", "minnesota"],
    "ne": ["patriots", "newengland", "new_england"],
    "no": ["saints", "neworleans", "new_orleans"],
    "nyg": ["giants", "newyork", "new_york"],
    "nyj": ["jets", "newyork", "new_york"],
    "phi": ["eagles", "philadelphia"],
    "pit": ["steelers", "pittsburgh"],
    "sf": ["49ers", "niners", "sanfrancisco", "san_francisco"],
    "sea": ["seahawks", "seattle"],
    "tb": ["buccaneers", "bucs", "tampa", "tampabay", "tampa_bay"],
    "ten": ["titans", "tennessee"],
    "wsh": ["commanders", "washington"],
}


class SportsDisplay(BaseDisplay):
    def __init__(self, config):
        team_id = int(config.get("NFL", "team_id", fallback="11"))
        team_abbr = config.get("NFL", "team_abbr", fallback="IND")
        team_name = config.get("NFL", "team_name", fallback="Indianapolis Colts")
        team_timezone = config.get("NFL", "team_timezone", fallback="America/Chicago")
        self.panel_duration = int(config.get("NFL", "panel_seconds", fallback="8"))
        self.service = NFLService(
            team_id=team_id,
            team_abbr=team_abbr,
            team_name=team_name,
            team_timezone=team_timezone,
        )
        self.logger = logging.getLogger(__name__)
        self.logo_cache = {}
        self.team_abbr = team_abbr
        self.team_name = team_name
        self.config = config
        env_name = config.get("Environment", "name", fallback="prod").lower()
        custom_root = config.get("NFL", "logos_root", fallback="").strip()
        base_dir = None
        if custom_root:
            base_dir = Path(custom_root).expanduser()
            self.logger.info("Using custom NFL logo root: %s", base_dir)
        elif env_name == "prod":
            # Default Raspberry Pi install location for prod
            base_dir = Path("/home/krjamies/raspberry_pi_led/app").expanduser()
            self.logger.info("Using prod NFL logo root: %s", base_dir)
        else:
            base_dir = Path(__file__).resolve().parents[1]

        logos_dir = base_dir / "assets" / "nfl_logos"
        if not logos_dir.exists():
            fallback_dir = Path(__file__).resolve().parents[1] / "assets" / "nfl_logos"
            self.logger.warning(
                "Logos directory %s not found; falling back to %s",
                logos_dir,
                fallback_dir,
            )
            logos_dir = fallback_dir

        self.logos_dir = logos_dir
        self.team_lookup = {
            "12": {"abbr": "KC", "nickname": "Chiefs", "name": "Kansas City Chiefs"},
            "11": {"abbr": "IND", "nickname": "Colts", "name": "Indianapolis Colts"},
        }

    def display(self, canvas, font_large, font_small):
        self.clear_canvas(canvas)

        # Prefer live schedule; fall back to config overrides
        game = self.service.get_next_game()
        if not game:
            self.logger.warning("No live NFL game found; using config fallback.")
            game = {}

        opponent_id = game.get("opponent_id")
        opponent_name = game.get("opponent_name") or self.config.get(
            "NFL", "opponent_name", fallback=""
        )
        opponent_nickname = game.get("opponent_nickname") or self.config.get(
            "NFL", "opponent_nickname", fallback=""
        )
        opponent_abbr = game.get("opponent_abbr") or self.config.get(
            "NFL", "opponent_abbr", fallback=""
        )

        # Enrich from local team lookup by id if present
        if opponent_id and opponent_id in self.team_lookup:
            info = self.team_lookup[opponent_id]
            opponent_abbr = opponent_abbr or info.get("abbr", "")
            opponent_name = opponent_name or info.get("name", "")
            opponent_nickname = opponent_nickname or info.get("nickname", "")

        if not opponent_nickname and opponent_name:
            tokens = opponent_name.split()
            opponent_nickname = tokens[-1] if tokens else opponent_name

        if not opponent_abbr and opponent_nickname:
            opponent_abbr = opponent_nickname[:3].upper()
        if not opponent_abbr:
            self.logger.warning("Opponent abbreviation missing; logo lookup may fail.")

        if not opponent_name:
            opponent_name = "Opponent"
        if not opponent_nickname:
            opponent_nickname = opponent_name

        home_logo = self._get_logo_image(self.team_name, self.team_abbr, nickname=self.team_name)
        opp_logo = self._get_logo_image(
            opponent_name, opponent_abbr, nickname=opponent_nickname
        )

        left_x = 2
        right_x = 64 - (opp_logo.width if opp_logo else 0) - 2
        logo_y = 2

        if home_logo:
            canvas.SetImage(home_logo, left_x, logo_y)
        if opp_logo:
            canvas.SetImage(opp_logo, max(32, right_x), logo_y)

        # Show matchup line centered between logos
        vs_text = "VS"
        vs_color = graphics.Color(255, 215, 0)
        vs_x = 32 - self._measure_text(font_large, vs_text) // 2
        self.draw_text(
            canvas,
            font_large,
            vs_x,
            13,
            vs_color,
            vs_text,
        )

        # Show kickoff info
        kickoff = game.get("kickoff") or self.config.get("NFL", "kickoff_local", fallback="TBD")
        # Strip anything after "PM"/"AM" for brevity
        for marker in (" PM", " AM"):
            if marker in kickoff:
                kickoff = kickoff.split(marker)[0] + marker
                break
        info_text = kickoff
        info_color = graphics.Color(255, 200, 0)  # amber/gold
        info_width = self._measure_text(font_small, info_text)
        info_x = max(0, (64 - info_width) // 2)
        self.draw_text(
            canvas,
            font_small,
            info_x,
            30,
            info_color,
            info_text[:62],
        )

    def _measure_text(self, font, text):
        width = 0
        for char in text:
            try:
                width += font.CharacterWidth(ord(char))
            except AttributeError:
                width += 6
        return width

    def _get_logo_image(self, team_name: str, team_abbr: str, nickname: str = "") -> Optional[Image.Image]:
        key = (team_name.lower().strip(), team_abbr.lower().strip(), nickname.lower().strip())
        if key in self.logo_cache:
            return self.logo_cache[key]

        logo = self._load_logo_from_disk(team_name, team_abbr, nickname)
        if not logo:
            self.logger.warning("No logo found for %s (%s) in %s", team_name, team_abbr, self.logos_dir)
        self.logo_cache[key] = logo
        return logo

    def _load_logo_from_disk(self, team_name: str, team_abbr: str, nickname: str) -> Optional[Image.Image]:
        """Load a team logo PNG from app/assets/nfl_logos by matching abbreviation/name."""
        if not self.logos_dir.exists():
            return None
        safe_abbr = (team_abbr or "").lower()
        name_tokens = [tok for tok in (team_name or "").lower().replace("-", " ").split() if tok]
        search_terms = []
        # Prefer the nickname (e.g., chiefs.png, colts.png)
        nick = nickname.lower().strip() if nickname else ""
        if nick:
            search_terms.append(nick)
        if name_tokens:
            search_terms.append(name_tokens[-1])
        if safe_abbr:
            search_terms.append(safe_abbr)
        if len(name_tokens) > 1:
            search_terms.append("".join(name_tokens))
        search_terms.extend(LOGO_ABBR_ALIASES.get(safe_abbr, []))
        best_path = None
        for path in self.logos_dir.iterdir():
            if not path.is_file() or path.suffix.lower() != ".png":
                continue
            stem = path.stem.lower()
            if any(term and term in stem for term in search_terms):
                best_path = path
                break
        if not best_path:
            return None
        try:
            img = self._open_logo(best_path)
            if not img:
                return None
            resized = self._resize_logo(img, target_height=22)
            return resized
        except Exception as exc:
            self.logger.warning("Failed loading logo %s: %s", best_path, exc)
            return None

    def _open_logo(self, path: Path) -> Optional[Image.Image]:
        try:
            return Image.open(path).convert("RGB")
        except Exception as exc:
            self.logger.warning("Logo open failed for %s: %s", path, exc)
            return None

    def _resize_logo(self, img: Image.Image, target_height: int) -> Image.Image:
        if img.height <= target_height:
            return img
        ratio = target_height / float(img.height)
        target_width = max(1, int(img.width * ratio))
        return img.resize((target_width, target_height), Image.LANCZOS)
