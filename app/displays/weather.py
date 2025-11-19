from ..matrix.helper import graphics
from ..services.weather import Weather
from .base import BaseDisplay


class WeatherDisplay(BaseDisplay):
    def __init__(self, config):
        self.city = config["Weather"].get("city", "Austin")
        cache_ttl = int(config["Weather"].get("cache_ttl_seconds", "600"))
        api_key = config["Weather"]["api_key"]
        self.weather = Weather(api_key, city=self.city, cache_ttl_seconds=cache_ttl)
        self.current_panel_duration = int(
            config["Weather"].get("current_panel_seconds", "25")
        )
        self.forecast_panel_duration = int(
            config["Weather"].get("forecast_panel_seconds", "20")
        )
        self.marquee_panel_duration = int(
            config["Weather"].get("marquee_panel_seconds", "15")
        )
        self.icon_cache = {}
        self.display_width = int(config.get("RGBMatrix", "cols", fallback="64"))
        self.scroll_speed = max(
            1, int(config["Weather"].get("scroll_speed_pixels", "1"))
        )
        self.marquee_message = ""
        self.marquee_x = float(self.display_width)

    def render_current(self, canvas, font_large, font_small, font_mini):
        weather_data = self.weather.get_current_weather()
        if not weather_data:
            self.draw_text(
                canvas, font_large, 16, 22, graphics.Color(255, 255, 255), "N/A"
            )
            return

        main_section = weather_data.get("main", {})
        temperature = main_section.get("temp")
        feels_like = main_section.get("feels_like")
        degree_symbol = chr(176)

        weather = weather_data.get("weather") or [{}]
        weather_icon_code = weather[0].get("icon")
        weather_icon = self._get_icon(weather_icon_code)

        if weather_icon:
            icon = weather_icon.copy()
            icon.thumbnail((18, 18))
            canvas.SetImage(icon.convert("RGB"), 4, 12)

        text_x = 32
        if temperature is not None:
            temp_text = f"{int(temperature)}{degree_symbol}F"
            self.draw_text(
                canvas,
                font_large,
                text_x,
                18,
                graphics.Color(255, 255, 255),
                temp_text,
            )

        if feels_like is not None:
            feels_text = f"Feels {int(feels_like)}{degree_symbol}"
            self.draw_text(
                canvas,
                font_mini,
                text_x,
                28,
                graphics.Color(173, 216, 230),
                feels_text.upper(),
            )

    def render_forecast(self, canvas, font_small):
        forecast = self.weather.get_multi_day_forecast(days=3)
        if not forecast:
            last_refresh = self.weather.last_forecast_refresh() or "--:--"
            self.draw_text(
                canvas,
                font_small,
                4,
                18,
                graphics.Color(255, 255, 255),
                f"No forecast (last {last_refresh})",
            )
            return

        high_color = graphics.Color(255, 165, 0)
        low_color = graphics.Color(135, 206, 250)
        label_color = graphics.Color(200, 200, 200)
        columns = len(forecast)
        column_width = max(18, 64 // columns)
        divider_color = graphics.Color(45, 60, 80)
        for idx, day_data in enumerate(forecast):
            x_start = idx * column_width
            x_center = x_start + column_width // 2
            if idx and idx < columns:
                graphics.DrawLine(canvas, x_start, 10, x_start, 31, divider_color)

            label = day_data.get("day")
            if label:
                label_text = label[:3]
                label_x = max(
                    0, x_center - self._measure_text(font_small, label_text) // 2
                )
                self.draw_text(canvas, font_small, label_x, 8, label_color, label_text)

            icon = self._get_icon(day_data.get("icon"))
            if icon:
                resized = icon.copy()
                resized.thumbnail((16, 12))
                icon_x = max(0, x_center - resized.width // 2)
                canvas.SetImage(resized.convert("RGB"), icon_x, 12)

            high_text = f"{int(day_data['high'])}°"
            low_text = f"{int(day_data['low'])}°"
            high_x = max(
                0, x_center - self._measure_text(font_small, high_text) // 2
            )
            low_x = max(0, x_center - self._measure_text(font_small, low_text) // 2)
            self.draw_text(canvas, font_small, high_x, 25, high_color, high_text)
            self.draw_text(canvas, font_small, low_x, 30, low_color, low_text)

    def render_marquee(self, canvas, font_small):
        weather_data = self.weather.get_current_weather()
        description = ""
        if weather_data:
            weather = weather_data.get("weather") or [{}]
            description = (weather[0].get("description") or "").strip().title()
        message = (
            f"{self.city} Weather Report: {description}"
            if description
            else f"{self.city} Weather Report"
        )
        if message != self.marquee_message:
            self.marquee_message = message
            self.marquee_x = float(self.display_width)

        scroll_width = self._measure_text(font_small, self.marquee_message)
        self.draw_text(
            canvas,
            font_small,
            int(self.marquee_x),
            20,
            graphics.Color(173, 216, 230),
            self.marquee_message,
        )
        self.marquee_x -= self.scroll_speed
        if self.marquee_x + scroll_width < 0:
            self.marquee_x = float(self.display_width)

    def _get_icon(self, icon_code):
        if not icon_code:
            return None
        if icon_code not in self.icon_cache:
            self.icon_cache[icon_code] = self.weather.get_weather_icon(icon_code)
        return self.icon_cache[icon_code]

    def _measure_text(self, font, text):
        width = 0
        for char in text:
            try:
                width += font.CharacterWidth(ord(char))
            except AttributeError:
                width += 6
        return width

