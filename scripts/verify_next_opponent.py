"""
Quick validation script to confirm we can identify the Colts' next opponent
and resolve the matching logo file on disk.

Usage:
    python -m scripts.verify_next_opponent
"""

import logging
from pathlib import Path

from app.config import load_config
from app.displays.sports import SportsDisplay, LOGO_ABBR_ALIASES


def resolve_opponent_info(display: SportsDisplay):
    """Mirror SportsDisplay.display() opponent selection without rendering."""
    game = display.service.get_next_game() or {}
    config = display.config

    opponent_id = game.get("opponent_id")
    opponent_name = game.get("opponent_name") or config.get("NFL", "opponent_name", fallback="")
    opponent_nickname = game.get("opponent_nickname") or config.get(
        "NFL", "opponent_nickname", fallback=""
    )
    opponent_abbr = game.get("opponent_abbr") or config.get("NFL", "opponent_abbr", fallback="")

    if opponent_id and opponent_id in display.team_lookup:
        info = display.team_lookup[opponent_id]
        opponent_abbr = opponent_abbr or info.get("abbr", "")
        opponent_name = opponent_name or info.get("name", "")
        opponent_nickname = opponent_nickname or info.get("nickname", "")

    if not opponent_nickname and opponent_name:
        tokens = opponent_name.split()
        opponent_nickname = tokens[-1] if tokens else opponent_name

    if not opponent_abbr and opponent_nickname:
        opponent_abbr = opponent_nickname[:3].upper()

    if not opponent_name:
        opponent_name = "Opponent"
    if not opponent_nickname:
        opponent_nickname = opponent_name

    return {
        "opponent_id": opponent_id,
        "opponent_name": opponent_name,
        "opponent_nickname": opponent_nickname,
        "opponent_abbr": opponent_abbr,
        "kickoff": game.get("kickoff"),
        "venue": game.get("venue"),
        "home": game.get("home"),
        "source_game": bool(game),
    }


def find_logo_path(display: SportsDisplay, team_name: str, team_abbr: str, nickname: str):
    """Replicates _load_logo_from_disk but returns the file path instead of an image."""
    logos_dir = display.logos_dir
    if not logos_dir.exists():
        return None

    safe_abbr = (team_abbr or "").lower()
    name_tokens = [tok for tok in (team_name or "").lower().replace("-", " ").split() if tok]
    search_terms = []
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

    for path in logos_dir.iterdir():
        if not path.is_file() or path.suffix.lower() != ".png":
            continue
        stem = path.stem.lower()
        if any(term and term in stem for term in search_terms):
            return path
    return None


def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    config = load_config()
    display = SportsDisplay(config)

    info = resolve_opponent_info(display)
    if not info["source_game"]:
        logging.warning("No live schedule data returned; using config overrides only.")

    logging.info(
        "Next opponent: %s (%s) nickname=%s home=%s kickoff=%s venue=%s",
        info["opponent_name"],
        info["opponent_abbr"],
        info["opponent_nickname"],
        info["home"],
        info["kickoff"],
        info["venue"],
    )

    logo_path = find_logo_path(
        display,
        info["opponent_name"],
        info["opponent_abbr"],
        info["opponent_nickname"],
    )
    if logo_path:
        logging.info("Logo file located: %s", logo_path)
    else:
        logging.error(
            "Logo file NOT found for %s (%s) in %s",
            info["opponent_name"],
            info["opponent_abbr"],
            display.logos_dir,
        )

    # Basic exit signaling for CI usage
    if not logo_path:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
