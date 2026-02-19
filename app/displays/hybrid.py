# hybrid.py
from __future__ import annotations

from typing import Optional

from ..matrix.helper import graphics
from ..utils.datetime import format_display_datetime
from .base import BaseDisplay
from .glucose import GlucoseDisplay, GlucoseCompactState
from .weather import WeatherDisplay, WeatherCompactState


class HybridDisplay(BaseDisplay):
    """
    Hybrid layout (64x32) combining:
      - Header: date/time (top bar)
      - Middle: glucose value + trend arrow in brackets, colored by glucose range
      - Bottom: temp + (small icon) + city
      - Optional: weather condition text in mini font (truncated)
    No delta shown.
    """

    def __init__(
        self,
        config,
        glucose_display: GlucoseDisplay,
        weather_display: WeatherDisplay,
    ):
        # keep config around in case you want to tweak layout via config later
        self.config = config
        self.glucose_display = glucose_display
        self.weather_display = weather_display
        self.display_width = int(config.get("RGBMatrix", "cols", fallback="64"))
        self.display_height = int(config.get("RGBMatrix", "rows", fallback="32"))

    # -------------------------
    # Text measurement helpers
    # -------------------------
    def _measure_text(self, font, text: str) -> int:
        width = 0
        for ch in text:
            try:
                width += font.CharacterWidth(ord(ch))
            except Exception:
                width += 6
        return width

    def _center_x(self, font, text: str) -> int:
        return max(0, (self.display_width - self._measure_text(font, text)) // 2)

    def _right_x(self, font, text: str, padding: int = 1) -> int:
        return max(0, self.display_width - padding - self._measure_text(font, text))

    def _truncate_to_width(self, font, text: str, max_width: int) -> str:
        if self._measure_text(font, text) <= max_width:
            return text
        ell = "…"
        if self._measure_text(font, ell) >= max_width:
            return ""
        out = text
        while out and self._measure_text(font, out + ell) > max_width:
            out = out[:-1]
        return out + ell if out else ""

    # -------------------------
    # Layout render
    # -------------------------
    def render(self, canvas, font_small, font_large, font_mini):
        """
        Expected fonts:
          - font_small: for header + bottom row
          - font_large: for glucose bracket row
          - font_mini: for optional condition text
        """
        canvas.Clear()

        # ----- Header (row baseline ~7)
        header = format_display_datetime()  # uses your existing formatting helper
        # keep header to one line; if you want "Feb 10th" later, update format_display_datetime()
        self.draw_text(
            canvas,
            font_small,
            1,
            7,
            graphics.Color(255, 165, 0),
            header,
        )

        # ----- Glucose (centered) baseline ~20
        g: Optional[GlucoseCompactState] = self.glucose_display.compact_state()
        if g:
            value_str = f"{g.value}" if g.value is not None else "--"
            trend_str = (g.trend or "").strip()
            mid = f"[ {value_str} {trend_str} ]" if trend_str else f"[ {value_str} ]"
            self.draw_text(
                canvas,
                font_large,
                self._center_x(font_large, mid),
                20,
                g.color,
                mid,
            )
        else:
            self.draw_text(
                canvas,
                font_small,
                1,
                20,
                graphics.Color(255, 255, 255),
                "No Readings",
            )

        # ----- Weather bottom line baseline ~31
        w: Optional[WeatherCompactState] = self.weather_display.compact_state()
        degree = chr(176)

        if w:
            temp_txt = f"{w.temp_f}{degree}" if w.temp_f is not None else f"--{degree}"
            city = (w.city or "").strip()

            # Draw the temperature first
            self.draw_text(
                canvas,
                font_small,
                1,
                31,
                graphics.Color(255, 255, 255),
                temp_txt,
            )

            # Draw small icon right after the temp (if present)
            next_x = 1 + self._measure_text(font_small, temp_txt) + 2  # padding after temp
            if w.icon:
                icon_x = next_x
                icon_y = 24  # good for ~12px icon on a 32px panel
                icon = self.weather_display._prepare_icon(w.icon, (12, 12))
                canvas.SetImage(icon.convert("RGB"), icon_x, icon_y)
                next_x = icon_x + icon.size[0] + 2  # padding after icon

            # Draw city after icon (or after temp if no icon)
            if city:
                self.draw_text(
                    canvas,
                    font_small,
                    next_x,
                    31,
                    graphics.Color(255, 255, 255),
                    city,
                )

        else:
            # no weather data
            self.draw_text(
                canvas,
                font_small,
                1,
                31,
                graphics.Color(255, 255, 255),
                f"--{degree} {self.weather_display.city}",
            )
