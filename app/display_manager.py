import logging
import time
from datetime import time as dtime
from pathlib import Path
from typing import Optional, Any, Dict, List

try:
    import schedule
except Exception:  # pragma: no cover - defensive import fallback
    import logging

    logging.getLogger(__name__).warning(
        "Optional dependency 'schedule' not available; scheduled jobs disabled."
    )

    class _DummyDay:
        def at(self, _time_str):
            return self

        def do(self, *args, **kwargs):
            return None

    class _DummyEvery:
        @property
        def day(self):
            return _DummyDay()

        def at(self, _time_str):
            return _DummyDay()

        def do(self, *args, **kwargs):
            return None

    class _DummyScheduleModule:
        def every(self):
            return _DummyEvery()

        def run_pending(self):
            return None

    schedule = _DummyScheduleModule()

from .matrix.helper import RGBMatrix, RGBMatrixOptions, graphics
from .displays.weather import WeatherDisplay
from .displays.glucose import GlucoseDisplay
from .displays.hybrid import HybridDisplay
from .renderer import Renderer
from .utils.cache import DataCache


class DisplayManager:
    """
    Hybrid-only orchestrator.

    This version only instantiates the required dependencies (glucose + weather)
    and renders a single HybridDisplay panel in a loop.
    """

    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger(__name__)

        # Shared in-memory cache for all data sources
        self.cache = DataCache(logger=self.logger)

        # Per-source TTLs (fall back to defaults if missing)
        self.cache_ttls = {
            "glucose": self._getint("CacheTTL", "glucose", 60),
            "weather_current": self._getint("CacheTTL", "weather_current", 600),
            "weather_forecast": self._getint("CacheTTL", "weather_forecast", 900),
        }

        # Matrix + renderer
        self.matrix = self.setup_matrix()
        self.renderer = Renderer(self.matrix, logger=self.logger)

        # Panels needed for hybrid
        self.glucose_display = GlucoseDisplay(
            config,
            data_cache=self.cache,
            cache_ttl_seconds=self.cache_ttls["glucose"],
        )
        self.weather_display = WeatherDisplay(
            config,
            data_cache=self.cache,
            cache_ttls=self.cache_ttls,
        )
        self.hybrid_display = HybridDisplay(
            config,
            glucose_display=self.glucose_display,
            weather_display=self.weather_display,
        )

        # Hybrid panel duration (reuse Dexcom panel_seconds fallback)
        self.hybrid_duration = int(config.get("Hybrid", "panel_seconds", fallback="10"))

        # Keep scheduled jobs alive (even though hybrid doesn’t need them)
        # This is harmless and keeps compatibility if you later add jobs.
        self.market_close_time = dtime(16, 0)
        schedule.every().day.at(self.market_close_time.strftime("%H:%M")).do(lambda: None)

    def setup_matrix(self):
        options = RGBMatrixOptions()

        if not self.config.has_section("RGBMatrix"):
            self.logger.warning("No [RGBMatrix] section found in config.ini; using defaults.")
        else:
            for key, value in self.config.items("RGBMatrix"):
                if not hasattr(options, key):
                    self.logger.warning("Unknown RGBMatrix option '%s'; skipping.", key)
                    continue

                current = getattr(options, key)
                raw = str(value)

                if isinstance(current, bool):
                    casted = raw.lower() in ("1", "true", "yes", "on")
                elif isinstance(current, int):
                    casted = int(raw)
                elif isinstance(current, float):
                    casted = float(raw)
                else:
                    casted = raw

                setattr(options, key, casted)
                self.logger.debug(
                    "RGBMatrix option %s set to %r (type %s)",
                    key,
                    casted,
                    type(casted).__name__,
                )

        # Apply sensible defaults for smoother rendering/flicker reduction
        try:
            configured_brightness = int(
                self.config.get("RGBMatrix", "brightness", fallback="85")
            )
            options.brightness = max(30, min(100, configured_brightness))
        except Exception:
            options.brightness = 70

        if not getattr(options, "limit_refresh_rate_hz", None):
            options.limit_refresh_rate_hz = 120

        if not getattr(options, "pwm_lsb_nanoseconds", None):
            options.pwm_lsb_nanoseconds = 130

        if not getattr(options, "gpio_slowdown", None):
            options.gpio_slowdown = 2

        return RGBMatrix(options=options)

    def run(self):
        script_dir = Path(__file__).resolve().parent
        font_dir = script_dir / "assets" / "fonts"

        font_small = graphics.Font()
        font_small.LoadFont(str(font_dir / "4x6.bdf"))

        font_large = graphics.Font()
        font_large.LoadFont(str(font_dir / "5x8.bdf"))

        font_mini = graphics.Font()
        font_mini.LoadFont(str(font_dir / "tom-thumb.bdf"))

        while True:
            # Use signatures so we only redraw when content changes.
            # We reuse the compact_state helpers you added.
            g = self.glucose_display.compact_state()
            w = self.weather_display.compact_state()

            signature = (
                "hybrid",
                g.value if g else None,
                g.trend if g else None,
                w.temp_f if w else None,
                # icon changes are rare; key off text/city + temp.
                w.city if w else None,
            )

            def draw(canvas):
                self.hybrid_display.render(canvas, font_small, font_large, font_mini)

            self.renderer.render("hybrid", signature, draw)
            self._sleep_with_pending(self.hybrid_duration)

    def _sleep_with_pending(self, seconds: float):
        end = time.monotonic() + max(seconds, 0)
        while time.monotonic() < end:
            time.sleep(min(0.5, end - time.monotonic()))
            schedule.run_pending()

    # -------------------------
    # Helpers
    # -------------------------
    def _getint(self, section: str, option: str, default: int) -> int:
        try:
            return self.config.getint(section, option, fallback=default)
        except Exception:
            return default
