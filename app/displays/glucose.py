# glucose_display.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Dict, Any

from ..services.blood_glucose import Glucose
from ..matrix.helper import graphics
from ..utils.cache import DataCache
from .base import BaseDisplay


@dataclass(frozen=True)
class GlucoseCompactState:
    """Small, reusable glucose state for composite layouts (e.g., HybridDisplay)."""
    value: int
    trend: str
    color: object  # graphics.Color


class GlucoseDisplay(BaseDisplay):
    def __init__(
        self,
        config,
        data_cache: Optional[DataCache] = None,
        cache_ttl_seconds: int = 60,
    ):
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

    def snapshot(self) -> Optional[Dict[str, Any]]:
        """Return the latest glucose reading in a simple dict form."""
        reading = self.glucose.get_glucose_reading()
        if not reading:
            return None
        return {"value": reading.mg_dl, "trend": reading.trend_arrow}

    # -------------------------
    # Shared helpers (reuse!)
    # -------------------------
    def _color_for_value(self, glucose_value: Optional[int]):
        """Determine text color based on glucose reading (single source of truth)."""
        if glucose_value is None:
            return graphics.Color(255, 255, 255)
        elif glucose_value <= 70:
            return graphics.Color(255, 0, 0)
        elif glucose_value <= 80:
            return graphics.Color(255, 255, 0)
        elif glucose_value <= 150:
            return graphics.Color(0, 255, 0)
        elif glucose_value <= 250:
            return graphics.Color(255, 255, 0)
        else:
            return graphics.Color(255, 0, 0)

    def compact_state(self, reading: Optional[Dict[str, Any]] = None) -> Optional[GlucoseCompactState]:
        """
        Return a compact, reusable state object for layouts that want the glucose value,
        trend arrow, and already-computed color without duplicating logic.
        """
        glucose_reading = reading or self.snapshot()
        if not glucose_reading:
            return None

        value = glucose_reading.get("value")
        trend = glucose_reading.get("trend") or ""
        color = self._color_for_value(value)
        return GlucoseCompactState(value=value, trend=trend, color=color)

    # -------------------------
    # Existing full-screen render
    # -------------------------
    def display(self, canvas, font_large, font_small, reading: Optional[dict] = None):
        """
        Render glucose on the canvas in the original format.
        Kept for backwards compatibility with DisplayManager.
        """
        glucose_reading = reading or self.snapshot()
        if glucose_reading:
            glucose_trend = glucose_reading.get("trend")
            glucose_value = glucose_reading.get("value")

            text_color = self._color_for_value(glucose_value)
            glucose_text = f"{glucose_value} {glucose_trend} mg/dl"
            self.draw_text(canvas, font_large, 4, 22, text_color, glucose_text)
        else:
            self.draw_text(canvas, font_small, 4, 22, graphics.Color(255, 255, 255), "No Readings")
