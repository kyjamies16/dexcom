import json
import logging
import time
import threading
from pathlib import Path

from ..services.stocks import Stock
from ..matrix.helper import graphics
from ..utils.cache import DataCache
from ..utils.datetime import format_display_datetime
from .base import BaseDisplay

logger = logging.getLogger(__name__)


class StockDisplay(BaseDisplay):
    def __init__(self, config, auto_refresh: bool = True, data_cache: DataCache = None, cache_ttl_seconds: int = 300):
        self.api_key = config["Stock"]["api_key"]
        self.stock_symbols = ['COST','TSM', 'LEN', 'GOOG', 'VOO', 'CAT', 'DXCM', 'MSFT', 'AXP']
        self.cache = data_cache or DataCache(logger=logger)
        self.cache_ttl_seconds = cache_ttl_seconds
        self.stocks = [Stock(self.api_key, symbol, cache=self.cache, cache_ttl_seconds=self.cache_ttl_seconds) for symbol in self.stock_symbols]
        self.current_stock_index = 0
        self.logger = logger
        self.request_interval = float(config["Stock"].get("request_interval_seconds", 12))
        repo_root = Path(__file__).resolve().parents[2]
        self.data_file = repo_root / "data" / "stock_data.json"
        self.display_width = int(config.get('RGBMatrix', 'cols', fallback='64'))
        self.scroll_x = self.display_width
        self.scroll_speed = int(config["Stock"].get("scroll_speed_pixels", 1))
        frame_interval = float(config["Stock"].get("scroll_frame_interval_seconds", 0.1))
        self.frame_interval = frame_interval if frame_interval > 0 else 0.1
        self.last_scroll_update = time.monotonic()
        self.stock_data_table = self.read_stock_data_from_file() or []
        self._refresh_thread = None

        # Fetch stock information asynchronously so UI isn't blocked
        if auto_refresh:
            self.async_refresh_stock_data()

    def fetch_all_stock_info(self):
        stock_data_table = []
        for index, stock in enumerate(self.stocks):
            stock_info = stock.get_stock_info()
            if stock_info:
                stock_data_table.append(stock_info)
            else:
                self.logger.warning("Skipping stock data for %s", stock.stock_symbol)

            # Respect AlphaVantage free-tier rate limits (5 requests/minute)
            if index < len(self.stocks) - 1:
                sleep_seconds = max(self.request_interval, 0)
                if sleep_seconds:
                    time.sleep(sleep_seconds)
        return stock_data_table

    def async_refresh_stock_data(self):
        if self._refresh_thread and self._refresh_thread.is_alive():
            return
        self._refresh_thread = threading.Thread(target=self.refresh_stock_data, daemon=True)
        self._refresh_thread.start()

    def refresh_stock_data(self):
        updated_data = self.fetch_all_stock_info()
        if updated_data:
            self.stock_data_table = updated_data
            self.write_stock_data_to_file()
            self.scroll_x = self.display_width
            self.logger.info("Stock data refreshed for %d symbols", len(updated_data))
        else:
            self.logger.warning("Stock data refresh skipped: no data returned")

    def reset_scroll(self):
        """Start the current ticker offscreen to the right for a fresh cycle."""
        self.scroll_x = self.display_width
        self.last_scroll_update = time.monotonic()

    def _current_text_width(self, font_small, font_large):
        if not self.stock_data_table:
            return 0
        stock_data = self.stock_data_table[self.current_stock_index % len(self.stock_data_table)]
        symbol_font = font_large if font_large else font_small
        symbol_width = self._measure_text(symbol_font, stock_data['symbol'])
        colon_width = self._measure_text(font_small, ": ")
        percent_text = self._format_percent_change(stock_data['percent_change'])
        percent_width = self._measure_text(font_small, percent_text)
        padding = 2
        return symbol_width + padding + colon_width + percent_width

    def fast_forward_scroll(self, elapsed_seconds, font_small, font_large=None):
        if not self.stock_data_table or elapsed_seconds <= 0:
            return
        steps = int(elapsed_seconds / self.frame_interval)
        if steps <= 0:
            return
        pixels_per_step = max(self.scroll_speed, 1)
        text_width = self._current_text_width(font_small, font_large)
        for _ in range(steps):
            self.scroll_x -= pixels_per_step
            # Treat reaching 0 or less as fully scrolled off the left edge; use <= to avoid "stuck at edge" cases
            if text_width and self.scroll_x + text_width <= 0:
                self.scroll_x = self.display_width
                self.current_stock_index = (
                    self.current_stock_index + 1
                ) % len(self.stock_data_table)
                text_width = self._current_text_width(font_small, font_large)
        self.last_scroll_update = time.monotonic()

    def _format_percent_change(self, percent_change_value):
        try:
            numeric_value = float(str(percent_change_value).strip('%'))
            return f"{numeric_value:.2f}%"
        except (ValueError, TypeError):
            self.logger.warning("Invalid percent_change value: %s", percent_change_value)
            return "--"
    def _measure_text(self, font, text):
        width = 0
        for char in text:
            try:
                width += font.CharacterWidth(ord(char))
            except AttributeError:
                width += 6
        return width

    def _get_percent_color(self, change):
        if change > 0:
            return graphics.Color(0, 255, 0)  # Green
        if change < 0:
            return graphics.Color(255, 0, 0)  # Red
        return graphics.Color(255, 255, 255)  # White

    def display(self, canvas, font_small, font_large=None):
        if not self.stock_data_table:
            self.logger.warning("No stock data available to display")
            return

        self.current_stock_index %= len(self.stock_data_table)
        stock_data = self.stock_data_table[self.current_stock_index]
        self.clear_canvas(canvas)
        if self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug("Displaying stock info: %s", stock_data)
        
        # Display current date and time at the top of the display
        self.draw_text(canvas, font_small, 2, 8, graphics.Color(255, 165, 0), format_display_datetime())
        
        if stock_data:
            symbol = stock_data['symbol']
            change = stock_data['change']
            percent_change_formatted = self._format_percent_change(
                stock_data['percent_change']
            )
            percent_color = self._get_percent_color(change)

            scroll_y = 22
            symbol_font = font_large if font_large else font_small
            symbol_width = self._measure_text(symbol_font, symbol)
            colon_text = ": "
            colon_width = self._measure_text(font_small, colon_text)
            percent_width = self._measure_text(font_small, percent_change_formatted)

            symbol_x = self.scroll_x
            padding = 2
            colon_x = symbol_x + symbol_width + padding
            percent_x = colon_x + colon_width

            self.draw_text(
                canvas,
                symbol_font,
                symbol_x,
                scroll_y,
                graphics.Color(135, 206, 250),
                symbol,
            )
            self.draw_text(
                canvas,
                font_small,
                colon_x,
                scroll_y,
                graphics.Color(255, 255, 255),
                colon_text,
            )
            self.draw_text(
                canvas,
                font_small,
                percent_x,
                scroll_y,
                percent_color,
                percent_change_formatted,
            )

            text_width = symbol_width + padding + colon_width + percent_width
            self.scroll_x -= max(self.scroll_speed, 1)
            # Use <= to ensure we reset once fully offscreen and avoid 1-pixel stuck states
            if text_width and self.scroll_x + text_width <= 0:
                self.scroll_x = self.display_width
                self.current_stock_index = (
                    self.current_stock_index + 1
                ) % len(self.stock_data_table)
            self.last_scroll_update = time.monotonic()

    def write_stock_data_to_file(self):
        if not self.stock_data_table:
            self.logger.warning("No stock data to persist; skipping save")
            return
        self.data_file.parent.mkdir(parents=True, exist_ok=True)
        with self.data_file.open('w') as file:
            json.dump(self.stock_data_table, file)

    def read_stock_data_from_file(self):
        if not self.data_file.exists():
            return []
        with self.data_file.open('r') as file:
            stock_data_table = json.load(file)
        return stock_data_table

