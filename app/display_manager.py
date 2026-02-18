import logging
import time
from datetime import datetime, time as dtime
from pathlib import Path
from typing import Optional, Any, Dict, List

import schedule

from .matrix.helper import RGBMatrix, RGBMatrixOptions, graphics
from .displays.weather import WeatherDisplay
from .displays.glucose import GlucoseDisplay
from .displays.stocks import StockDisplay
from .displays.sports import SportsDisplay
from .renderer import Renderer
from .utils.cache import DataCache
from .utils.datetime import format_display_datetime


class DisplayManager:
    """Central orchestrator: selects enabled panels, caches data, and redraws only when content changes."""
    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.mode = config.get("Environment", "mode", fallback="full").lower()
        self.cache = DataCache(logger=self.logger)  # shared in-memory cache for all data sources
        # Per-source TTLs (fall back to defaults if missing)
        self.cache_ttls = {
            "glucose": self._getint("CacheTTL", "glucose", 60),
            "weather_current": self._getint("CacheTTL", "weather_current", 600),
            "weather_forecast": self._getint("CacheTTL", "weather_forecast", 900),
            "stocks": self._getint("CacheTTL", "stocks", 300),
            "sports": self._getint("CacheTTL", "sports", 900),
        }

        # Feature toggles are derived from config + CLI mode (minimal/full)
        self.features = {
            "glucose": self._getbool("Features", "glucose", True),
            "weather": self._getbool("Features", "weather", True),
            "sports": self._getbool("Features", "sports", self.mode == "full"),
            "stocks": self._getbool("Features", "stocks", self.mode == "full"),
        }

        self.matrix = self.setup_matrix()
        self.renderer = Renderer(self.matrix, logger=self.logger)  # change-aware double buffering
        self.display_index = 0
        # Render order respects enabled features only
        self.display_order: List[str] = [
            name for name in ("glucose", "weather", "sports", "stocks") if self.features.get(name)
        ]
        if not self.display_order:
            self.logger.warning("No displays enabled; enable features in config/CLI mode.")

        # Panels
        self.glucose_display: Optional[GlucoseDisplay] = None
        self.weather_display: Optional[WeatherDisplay] = None
        self.stock_display: Optional[StockDisplay] = None
        self.sports_display: Optional[SportsDisplay] = None

        if self.features["glucose"]:
            self.glucose_display = GlucoseDisplay(
                config,
                data_cache=self.cache,
                cache_ttl_seconds=self.cache_ttls["glucose"],
            )
        if self.features["weather"]:
            self.weather_display = WeatherDisplay(
                config,
                data_cache=self.cache,
                cache_ttls=self.cache_ttls,
            )
        if self.features["stocks"]:
            self.stock_display = StockDisplay(
                config,
                auto_refresh=True,
                data_cache=self.cache,
                cache_ttl_seconds=self.cache_ttls["stocks"],
            )
        if self.features["sports"]:
            self.sports_display = SportsDisplay(
                config,
                data_cache=self.cache,
                cache_ttl_seconds=self.cache_ttls["sports"],
            )

        # Kick off stock refresh at market close daily (4 PM local)
        self.market_close_time = dtime(16, 0)
        schedule.every().day.at(self.market_close_time.strftime("%H:%M")).do(
            self.fetch_stock_data_on_market_close
        )

        self.stock_cycle_duration = int(
            config.get("Stock", "cycle_seconds", fallback="30")
        )
        self.glucose_duration = int(
            config.get("Dexcom", "panel_seconds", fallback="10")
        )

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
                    # str or any other custom type
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

    def fetch_stock_data_on_market_close(self):
        if not self.stock_display:
            return
        self.logger.info("Triggering scheduled stock refresh at market close")
        self.stock_display.async_refresh_stock_data()

    def run(self):
        script_dir = Path(__file__).resolve().parent
        font_dir = script_dir / "assets" / "fonts"
        font_small = graphics.Font()
        font_small.LoadFont(str(font_dir / "4x6.bdf"))  # Use a smaller font

        font_large = graphics.Font()
        font_large.LoadFont(str(font_dir / "5x8.bdf"))

        font_mini = graphics.Font()
        font_mini.LoadFont(str(font_dir / "tom-thumb.bdf"))

        while True:
            if not self.display_order:
                time.sleep(1)
                schedule.run_pending()
                continue

            # Cycle through enabled panels; per-panel renderer decides if redraw is needed
            panel = self.display_order[self.display_index % len(self.display_order)]
            if panel == "glucose" and self.glucose_display:
                self._render_glucose(font_small, font_large)
            elif panel == "weather" and self.weather_display:
                self._render_weather_cycle(font_small, font_large, font_mini)
            elif panel == "sports" and self.sports_display:
                self._render_sports(font_small, font_large)
            elif panel == "stocks" and self.stock_display:
                self._render_stock_cycle(font_small, font_large)

            self.display_index = (self.display_index + 1) % len(self.display_order)
            schedule.run_pending()

    def _draw_header(self, canvas, font_small, text: str, highlight: bool = False):
        color = graphics.Color(200, 120, 0) if highlight else graphics.Color(255, 165, 0)
        canvas.Clear()
        canvas = canvas or self.matrix.CreateFrameCanvas()
        self._draw_header_text(canvas, font_small, text, color)

    def _draw_header_text(self, canvas, font_small, text: str, color):
        self._safe_draw_text(canvas, font_small, 2, 8, color, text)

    def _safe_draw_text(self, canvas, font, x, y, color, text):
        return graphics.DrawText(canvas, font, x, y, color, text)

    def _sleep_with_pending(self, seconds: float):
        # Sleep in short slices so scheduled jobs (like stock refresh) still run
        end = time.monotonic() + max(seconds, 0)
        while time.monotonic() < end:
            time.sleep(min(0.5, end - time.monotonic()))
            schedule.run_pending()

    # -------------------------
    # Panel renderers
    # -------------------------
    def _render_glucose(self, font_small, font_large):
        header_text = format_display_datetime()
        reading = self.glucose_display.snapshot() if self.glucose_display else None
        signature = ("glucose", header_text, reading and reading.get("value"), reading and reading.get("trend"))

        def draw(canvas):
            canvas.Clear()
            self._draw_header_text(canvas, font_small, header_text, graphics.Color(255, 165, 0))
            self.glucose_display.display(canvas, font_large, font_small, reading=reading)

        self.renderer.render("glucose", signature, draw)
        self._sleep_with_pending(self.glucose_duration)

    def _render_sports(self, font_small, font_large):
        header_text = format_display_datetime()
        game = self.sports_display.snapshot() if self.sports_display else {}
        signature = (
            "sports",
            header_text,
            game.get("opponent_abbr"),
            game.get("kickoff"),
        )

        def draw(canvas):
            canvas.Clear()
            self._draw_header_text(canvas, font_small, header_text, graphics.Color(200, 120, 0))
            self.sports_display.display(canvas, font_large, font_small)

        self.renderer.render("sports", signature, draw)
        self._sleep_with_pending(int(self.config.get("NFL", "panel_seconds", fallback="8")))

    def _render_weather_cycle(self, font_small, font_large, font_mini):
        header_text = format_display_datetime()
        weather_data = self.weather_display.snapshot_current() if self.weather_display else None
        forecast = self.weather_display.snapshot_forecast() if self.weather_display else None

        # Marquee (animated) redraws until finished or duration elapsed
        marquee_end = time.monotonic() + max(self.weather_display.marquee_panel_duration, 5)
        finished = False
        while time.monotonic() < marquee_end:
            message = self.weather_display.marquee_signature(weather_data)
            marquee_sig = (
                "weather-marquee",
                header_text,
                message,
                int(self.weather_display.marquee_x),
            )

            def draw(canvas):
                nonlocal finished
                canvas.Clear()
                self._draw_header_text(canvas, font_small, header_text, graphics.Color(200, 120, 0))
                finished = self.weather_display.render_marquee(canvas, font_small, weather_data)

            self.renderer.render("weather-marquee", marquee_sig, draw, force=True)
            if finished:
                break
            time.sleep(0.06)
            schedule.run_pending()

        # Current conditions (static)
        current_sig = (
            "weather-current",
            header_text,
            self._current_signature(weather_data),
        )

        def draw_current(canvas):
            canvas.Clear()
            self._draw_header_text(canvas, font_small, header_text, graphics.Color(200, 120, 0))
            self.weather_display.render_current(
                canvas, font_large, font_small, font_mini, weather_data
            )

        self.renderer.render("weather-current", current_sig, draw_current)
        self._sleep_with_pending(self.weather_display.current_panel_duration)

        # Forecast (static)
        forecast_sig = ("weather-forecast", header_text, self._forecast_signature(forecast))

        def draw_forecast(canvas):
            canvas.Clear()
            self.weather_display.render_forecast(canvas, font_small, forecast)

        self.renderer.render("weather-forecast", forecast_sig, draw_forecast)
        self._sleep_with_pending(self.weather_display.forecast_panel_duration)

    def _render_stock_cycle(self, font_small, font_large):
        if not self.stock_display:
            return
        # Ensure ticker starts from the right edge each cycle
        self.stock_display.reset_scroll()
        now_monotonic = time.monotonic()
        idle_elapsed = now_monotonic - getattr(
            self.stock_display, "last_scroll_update", now_monotonic
        )
        if idle_elapsed > 0:
            self.stock_display.fast_forward_scroll(idle_elapsed, font_small, font_large)
        cycle_end = time.monotonic() + self.stock_cycle_duration
        frame_delay = max(self.stock_display.frame_interval, 0.05)

        while time.monotonic() < cycle_end:
            signature = (
                "stocks",
                self.stock_display.current_stock_index,
                int(self.stock_display.scroll_x),
                len(self.stock_display.stock_data_table or []),
            )

            def draw(canvas):
                self.stock_display.display(canvas, font_small, font_large)

            self.renderer.render("stocks", signature, draw, force=True)
            time.sleep(frame_delay)
            schedule.run_pending()

    # -------------------------
    # Signatures
    # -------------------------
    def _current_signature(self, weather_data: Optional[Dict[str, Any]]):
        if not weather_data:
            return None
        main = weather_data.get("main", {})
        weather = (weather_data.get("weather") or [{}])[0]
        return (
            int(main.get("temp", 0)),
            int(main.get("feels_like", 0)),
            weather.get("icon"),
            weather.get("description"),
        )

    def _forecast_signature(self, forecast: Optional[List[Dict[str, Any]]]):
        if not forecast:
            return None
        simplified = []
        for day in forecast:
            simplified.append(
                (
                    day.get("day"),
                    int(day.get("high", 0)),
                    int(day.get("low", 0)),
                    day.get("icon"),
                )
        )
        return tuple(simplified)

    # -------------------------
    # Helpers
    # -------------------------
    def _getbool(self, section: str, option: str, default: bool) -> bool:
        try:
            return self.config.getboolean(section, option, fallback=default)
        except Exception:
            return default

    def _getint(self, section: str, option: str, default: int) -> int:
        try:
            return self.config.getint(section, option, fallback=default)
        except Exception:
            return default
