import configparser
from functools import lru_cache
from pathlib import Path
from typing import List


def _config_search_paths() -> List[Path]:
    base_dir = Path(__file__).resolve().parent.parent
    return [
        Path("config.ini"),
        base_dir / "config.ini",
        base_dir / "congfig.ini",
        base_dir / "venv" / "Scripts" / "config.ini",  # legacy fallback
        base_dir / "venv" / "Scripts" / "congfig.ini",
    ]


@lru_cache()
def load_config() -> configparser.ConfigParser:
    config = configparser.ConfigParser()
    readable = [str(path) for path in _config_search_paths() if path.exists()]
    if not readable:
        raise FileNotFoundError(
            "Unable to locate config.ini. "
            "Checked: {}".format(", ".join(str(path) for path in _config_search_paths()))
        )
    config.read(readable)
    return config
