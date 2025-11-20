import logging
from pathlib import Path
from typing import Optional

from PIL import Image, ImageDraw

from ..matrix.helper import graphics
from ..services.nfl import NFLService
from .base import BaseDisplay


COLTS_BLUE = (0, 44, 95)
COLTS_WHITE = (240, 240, 240)
CHIEFS_RED = (181, 0, 16)
CHIEFS_GOLD = (255, 184, 28)


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
        self.logos_dir = Path(__file__).resolve().parents[1] / "assets" / "nfl_logos"

    def display(self, canvas, font_large, font_small):
        self.clear_canvas(canvas)

        # Prefer live schedule; fall back to optional manual override
        game = self.service.get_next_game()
        if not game:
            game = {
                "opponent_abbr": self.config.get("NFL", "opponent_abbr", fallback=""),
                "opponent_name": self.config.get("NFL", "opponent_name", fallback=""),
                "home": self.config.getboolean("NFL", "home", fallback=True),
                "kickoff": self.config.get("NFL", "kickoff_local", fallback="TBD"),
                "venue": self.config.get("NFL", "venue", fallback=""),
            }
        if not game:
            self.draw_text(
                canvas,
                font_small,
                2,
                16,
                graphics.Color(255, 255, 255),
                f"{self.team_abbr} schedule TBD",
            )
            return

        home_logo = self._get_logo_image(self.team_name, self.team_abbr)
        opp_logo = self._get_logo_image(
            game.get("opponent_name", ""), game.get("opponent_abbr", "")
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
        kickoff = game.get("kickoff", "TBD")
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

    def _get_logo_image(self, team_name: str, team_abbr: str) -> Optional[Image.Image]:
        key = (team_name.lower().strip(), team_abbr.lower().strip())
        if key in self.logo_cache:
            return self.logo_cache[key]

        logo = self._load_logo_from_disk(team_name, team_abbr)
        if logo:
            self.logo_cache[key] = logo
            return logo

        # Fallback pixel art for Colts/Opponent if nothing found
        if team_abbr.upper() == self.team_abbr.upper():
            logo = self._build_colts_logo()
        elif team_abbr.upper() == "KC":
            logo = self._build_chiefs_logo()
        elif team_abbr.upper() == "IND":
            logo = self._build_colts_logo()
        if not logo:
            self.logger.warning("Using fallback pixel logo for %s (%s)", team_name, team_abbr)
        self.logo_cache[key] = logo
        return logo

    def _load_logo_from_disk(self, team_name: str, team_abbr: str) -> Optional[Image.Image]:
        if not self.logos_dir.exists():
            return None
        safe_abbr = (team_abbr or "").lower()
        name_tokens = [tok for tok in (team_name or "").lower().replace("-", " ").split() if tok]
        alias_map = {
            "kc": ["chiefs", "kansascity", "kansascity", "kansas-city"],
            "ind": ["colts", "indianapolis", "indy"],
        }
        search_terms = []
        if safe_abbr:
            search_terms.append(safe_abbr)
            search_terms.extend(alias_map.get(safe_abbr, []))
        search_terms.extend(["".join(name_tokens), *name_tokens])
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

    def _build_colts_logo(self) -> Optional[Image.Image]:
        """Generate a compact Colts horseshoe (optimized for 64x32)."""
        try:
            size = 30
            img = Image.new("RGB", (size, size), (0, 0, 0))
            draw = ImageDraw.Draw(img)

            outer = 2
            inner = 9
            stroke = 4

            draw.arc(
                [outer, outer, size - outer, size - outer],
                start=210,
                end=330,
                fill=COLTS_BLUE,
                width=stroke,
            )
            draw.arc(
                [outer, outer, size - outer, size - outer],
                start=30,
                end=150,
                fill=COLTS_BLUE,
                width=stroke,
            )

            draw.rectangle([outer + 2, 10, outer + 6, size - 8], fill=COLTS_BLUE)
            draw.rectangle([size - 8, 10, size - 4, size - 8], fill=COLTS_BLUE)

            draw.ellipse(
                [inner, inner, size - inner, size - inner],
                fill=(0, 0, 0),
            )

            hole_r = 2
            holes = [
                (size // 2, outer + 6),
                (size // 2, size - outer - 6),
                (outer + 6, size // 2 - 4),
                (outer + 6, size // 2 + 4),
                (size - outer - 6, size // 2 - 4),
                (size - outer - 6, size // 2 + 4),
                (size // 2 - 7, size // 2),
                (size // 2 + 7, size // 2),
            ]
            for x, y in holes:
                draw.ellipse(
                    [x - hole_r, y - hole_r, x + hole_r, y + hole_r],
                    fill=COLTS_WHITE,
                )

            return img
        except Exception as exc:
            self.logger.warning("Failed to build Colts logo: %s", exc)
            return None

    def _build_chiefs_logo(self) -> Optional[Image.Image]:
        """Generate a small Chiefs arrowhead style icon."""
        try:
            width, height = 30, 20
            img = Image.new("RGB", (width, height), (0, 0, 0))
            draw = ImageDraw.Draw(img)

            points = [
                (2, height // 2),
                (8, 2),
                (23, 2),
                (27, height // 2),
                (23, height - 2),
                (8, height - 2),
            ]
            draw.polygon(points, fill=CHIEFS_RED, outline=CHIEFS_GOLD)

            k_strokes = [
                (10, 5, 12, 15),
                (12, 10, 15, 12),
                (12, 12, 15, 15),
            ]
            for coords in k_strokes:
                draw.rectangle(coords, fill=CHIEFS_GOLD)

            c_strokes = [
                (17, 6, 22, 8),
                (17, 8, 19, 14),
                (17, 14, 22, 16),
            ]
            for coords in c_strokes:
                draw.rectangle(coords, fill=CHIEFS_GOLD)

            return img
        except Exception as exc:
            self.logger.warning("Failed to build Chiefs logo: %s", exc)
            return None
