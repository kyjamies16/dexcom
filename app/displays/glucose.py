# glucose_display.py
from typing import Optional

from ..services.blood_glucose import Glucose
from ..matrix.helper import graphics
from ..utils.cache import DataCache
from .base import BaseDisplay


class GlucoseDisplay(BaseDisplay):
    def __init__(self, config, data_cache: Optional[DataCache] = None, cache_ttl_seconds: int = 60):
        dexcom_cfg = config["Dexcom"]
        self.cache_ttl_seconds = cache_ttl_seconds
        self.glucose = Glucose(
            username=dexcom_cfg.get("username"),
            password=dexcom_cfg.get("password"),
            account_id=dexcom_cfg.get("account_id"),
            region=dexcom_cfg.get("region", "us"),
            cache_ttl_seconds=cache_ttl_seconds,
            data_cache=data_cache,
        )

    def snapshot(self):
        reading = self.glucose.get_glucose_reading()
        if not reading:
            return None
        return {"value": reading.mg_dl, "trend": reading.trend_arrow}

    def display(self, canvas, font_large, font_small, reading: Optional[dict] = None):
        glucose_reading = reading or self.snapshot()
        if glucose_reading:
            glucose_trend = glucose_reading.get("trend")
            glucose_value = glucose_reading.get("value")

            # Determine text color based on glucose reading
            if glucose_value is None:
                text_color = graphics.Color(255, 255, 255)
            elif glucose_value <= 70:
                text_color = graphics.Color(255, 0, 0)
            elif glucose_value <= 80:
                text_color = graphics.Color(255, 255, 0)
            elif glucose_value <= 150:
                text_color = graphics.Color(0, 255, 0)
            elif glucose_value <= 250:
                text_color = graphics.Color(255, 255, 0)
            else:
                text_color = graphics.Color(255, 0, 0)

            glucose_text = f"{glucose_value} {glucose_trend} mg/dl"
            self.draw_text(canvas, font_large, 4, 22, text_color, glucose_text)
        else:
            self.draw_text(
                canvas, font_small, 4, 22, graphics.Color(255, 255, 255), "No Readings"
            )
