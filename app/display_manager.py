import logging
import time
from datetime import datetime, time as dtime
from pathlib import Path
from typing import Optional

import schedule

from .matrix.helper import RGBMatrix, RGBMatrixOptions, graphics
from .displays.weather import WeatherDisplay
from .displays.glucose import GlucoseDisplay
from .displays.stocks import StockDisplay
from .utils.datetime import format_display_datetime


class DisplayManager:
    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.weather_display = WeatherDisplay(config)
        self.glucose_display = GlucoseDisplay(config)
        self.stock_display = StockDisplay(config, auto_refresh=False)
        self.display_index = 0
        self.matrix = self.setup_matrix()
        self.sleep_duration = 5  # Initial sleep duration
        self.display_durations = [60, 60]
        self.stock_cycle_duration = 60
        self.stock_data_last_refresh: Optional[datetime] = None

        self.market_close_time = dtime(16, 0)
        schedule.every().day.at(self.market_close_time.strftime("%H:%M")).do(
            self.fetch_stock_data_on_market_close
        )

        if self.stock_display.stock_data_table:
            self.logger.info(
                "Loaded cached stock data for %d symbols",
                len(self.stock_display.stock_data_table),
            )
        else:
            self.logger.info(
                "No cached stock data found; awaiting 4 PM refresh for live updates"
            )

    def setup_matrix(self):
        options = RGBMatrixOptions()
        for key, value in self.config.items('RGBMatrix'):
            if hasattr(options, key):
                setattr(options, key, type(getattr(options, key))(value))
        if getattr(options, "brightness", None):
            options.brightness = max(20, int(options.brightness) // 2)
        else:
            options.brightness = 40
        return RGBMatrix(options=options)

    def is_market_closed(self):
        now = datetime.now().time()
        market_close_time = dtime(16, 0)  # Assuming market closes at 4 PM
        return now >= market_close_time

    def fetch_stock_data_on_market_close(self):
        self.logger.info("Triggering scheduled stock refresh at market close")
        self.stock_display.async_refresh_stock_data()
        self.stock_data_last_refresh = datetime.now()

    def display_text(self, canvas, font, x, y, color, text):
        graphics.DrawText(canvas, font, x, y, color, text)

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
            canvas = self.matrix.CreateFrameCanvas()
            header_color = (
                graphics.Color(200, 120, 0)
                if self.display_index == 1
                else graphics.Color(255, 165, 0)
            )
            self.display_text(canvas, font_small, 2, 8, header_color, format_display_datetime())

            if self.display_index == 0:
                # Display glucose data
                self.glucose_display.display(canvas, font_large, font_small)
                self.sleep_duration = self.display_durations[0]
                self.display_index = 1
                self.logger.info("Displaying glucose data")
            elif self.display_index == 1:
                self.logger.info("Displaying weather data")
                self._display_weather_cycle(font_small, font_large, font_mini)
                self.display_index = 2
                continue
            else:
                self._display_stock_cycle(font_small, font_large)
                self.display_index = 0
                continue

            # Update the LED matrix
            canvas = self.matrix.SwapOnVSync(canvas)
            time.sleep(self.sleep_duration)  # Sleep for configured duration

            # Run scheduled tasks
            schedule.run_pending()

    def _display_stock_cycle(self, font_small, font_large):
        now_monotonic = time.monotonic()
        idle_elapsed = now_monotonic - getattr(
            self.stock_display, "last_scroll_update", now_monotonic
        )
        if idle_elapsed > 0:
            self.stock_display.fast_forward_scroll(idle_elapsed, font_small, font_large)
        cycle_end = time.monotonic() + self.stock_cycle_duration
        frame_delay = 0.12

        while time.monotonic() < cycle_end:
            canvas = self.matrix.CreateFrameCanvas()
            if not self.stock_display.stock_data_table:
                self.logger.info(
                    "Stock data unavailable; displaying placeholder message"
                )
                self.display_text(
                    canvas,
                    font_small,
                    2,
                    8,
                    graphics.Color(255, 165, 0),
                    format_display_datetime(),
                )
                self.display_text(
                    canvas,
                    font_small,
                    2,
                    20,
                    graphics.Color(255, 255, 255),
                    "Stocks unavailable",
                )
                canvas = self.matrix.SwapOnVSync(canvas)
                time.sleep(1)
                schedule.run_pending()
                continue

            current_index = (
                self.stock_display.current_stock_index
                % len(self.stock_display.stock_data_table)
            )
            self.logger.info("Displaying stock data for index %d", current_index)
            self.stock_display.display(canvas, font_small, font_large)
            canvas = self.matrix.SwapOnVSync(canvas)
            time.sleep(frame_delay)
            schedule.run_pending()


    def _display_weather_cycle(self, font_small, font_large, font_mini):
        panels = [
            ("marquee", self.weather_display.marquee_panel_duration),
            ("current", self.weather_display.current_panel_duration),
            ("forecast", self.weather_display.forecast_panel_duration),
        ]
        frame_delay = 0.12
        for panel_type, duration in panels:
            cycle_end = time.monotonic() + max(duration, 5)
            while time.monotonic() < cycle_end:
                canvas = self.matrix.CreateFrameCanvas()
                if panel_type == "current":
                    self.display_text(
                        canvas,
                        font_small,
                        2,
                        8,
                        graphics.Color(200, 120, 0),
                        format_display_datetime(),
                    )
                    self.weather_display.render_current(
                        canvas, font_large, font_small, font_mini
                    )
                elif panel_type == "marquee":
                    self.display_text(
                        canvas,
                        font_small,
                        2,
                        8,
                        graphics.Color(200, 120, 0),
                        format_display_datetime(),
                    )
                    self.weather_display.render_marquee(canvas, font_small)
                else:
                    self.weather_display.render_forecast(canvas, font_small)
                canvas = self.matrix.SwapOnVSync(canvas)
                time.sleep(frame_delay)
                schedule.run_pending()



