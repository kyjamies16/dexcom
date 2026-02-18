import configparser
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover - optional in minimal mode
    yaml = None


def _config_search_paths() -> List[Path]:
    base_dir = Path(__file__).resolve().parent.parent
    return [
        Path("config.ini"),
        base_dir / "config.ini",
        base_dir / "congfig.ini",
        base_dir / "venv" / "Scripts" / "config.ini",  # legacy fallback
        base_dir / "venv" / "Scripts" / "congfig.ini",
    ]


def _settings_search_paths() -> List[Path]:
    base_dir = Path(__file__).resolve().parent.parent
    return [
        Path("settings.yaml"),
        base_dir / "settings.yaml",
        base_dir / "config" / "settings.yaml",
    ]


def _load_settings_yaml() -> Dict[str, Any]:
    if yaml is None:
        return {}
    for path in _settings_search_paths():
        if path.exists():
            with path.open("r", encoding="utf-8") as handle:
                return yaml.safe_load(handle) or {}
    return {}


def _apply_panel_defaults(config: configparser.ConfigParser, settings: Dict[str, Any]):
    panel_cfg: Dict[str, Any] = settings.get("panel") or {}
    if not panel_cfg:
        return
    if not config.has_section("RGBMatrix"):
        config.add_section("RGBMatrix")
    for key, value in panel_cfg.items():
        if not config.has_option("RGBMatrix", key):
            config.set("RGBMatrix", key, str(value))


def _apply_cache_defaults(
    config: configparser.ConfigParser, settings: Dict[str, Any]
):
    cache_cfg: Dict[str, Any] = settings.get("cache_ttl_seconds") or {}
    if not cache_cfg:
        return
    if not config.has_section("CacheTTL"):
        config.add_section("CacheTTL")
    for key, value in cache_cfg.items():
        if not config.has_option("CacheTTL", key):
            config.set("CacheTTL", key, str(value))


def _apply_mode_defaults(
    config: configparser.ConfigParser, mode: Optional[str], settings: Dict[str, Any]
):
    if not config.has_section("Environment"):
        config.add_section("Environment")
    if mode:
        config["Environment"]["mode"] = mode

    if not config.has_section("Features"):
        config.add_section("Features")

    selected_mode = (mode or config.get("Environment", "mode", fallback="full")).lower()
    mode_overrides = (settings.get("modes") or {}).get(selected_mode) or {}
    feature_overrides: Dict[str, Any] = mode_overrides.get("features") or {}

    defaults = {
        "glucose": True,
        "weather": True,
        "sports": selected_mode == "full",
        "stocks": selected_mode == "full",
    }
    for feature, enabled in {**defaults, **feature_overrides}.items():
        config["Features"][feature] = str(enabled)


@lru_cache()
def load_config(mode: Optional[str] = None) -> configparser.ConfigParser:
    config = configparser.ConfigParser()
    readable = [str(path) for path in _config_search_paths() if path.exists()]
    if not readable:
        raise FileNotFoundError(
            "Unable to locate config.ini. "
            "Checked: {}".format(", ".join(str(path) for path in _config_search_paths()))
        )
    config.read(readable)
    settings = _load_settings_yaml()
    _apply_panel_defaults(config, settings)
    _apply_cache_defaults(config, settings)
    _apply_mode_defaults(config, mode, settings)
    return config
