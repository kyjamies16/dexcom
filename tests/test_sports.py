import configparser
from pathlib import Path

import pytest

from app.displays.sports import SportsDisplay


def make_config(env_name="prod", logos_root=""):
    cfg = configparser.ConfigParser()
    cfg["Environment"] = {"name": env_name}
    cfg["NFL"] = {
        "team_id": "11",
        "team_abbr": "IND",
        "team_name": "Indianapolis Colts",
        "team_timezone": "America/Chicago",
    }
    if logos_root:
        cfg["NFL"]["logos_root"] = logos_root
    return cfg


def test_prod_env_prefers_rpi_logo_dir(monkeypatch):
    expected_dir = Path("/raspberry_pi_led/app/assets/nfl_logos")
    fake_files = [
        expected_dir / "colts.png",
        expected_dir / "chiefs.png",
    ]

    real_exists = Path.exists
    real_iterdir = Path.iterdir

    def fake_exists(self):
        if self == expected_dir or self in fake_files:
            return True
        return real_exists(self)

    def fake_iterdir(self):
        if self == expected_dir:
            return iter(fake_files)
        return real_iterdir(self)

    monkeypatch.setattr(Path, "exists", fake_exists)
    monkeypatch.setattr(Path, "iterdir", fake_iterdir)

    def fake_open_logo(self, path):
        return path

    def fake_resize(self, img, target_height):
        return img

    monkeypatch.setattr(SportsDisplay, "_open_logo", fake_open_logo)
    monkeypatch.setattr(SportsDisplay, "_resize_logo", fake_resize)

    display = SportsDisplay(make_config(env_name="prod"))

    assert display.logos_dir == expected_dir

    colts_logo = display._get_logo_image("Indianapolis Colts", "IND", nickname="Colts")
    chiefs_logo = display._get_logo_image("Kansas City Chiefs", "KC", nickname="Chiefs")

    assert colts_logo == expected_dir / "colts.png"
    assert chiefs_logo == expected_dir / "chiefs.png"
