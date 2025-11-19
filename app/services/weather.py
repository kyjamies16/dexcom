# weather.py
import logging
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from io import BytesIO
from typing import Any, Dict, List, Optional

import requests
from PIL import Image


class Weather:
    def __init__(self, api_key, city: str = "Austin", cache_ttl_seconds: int = 600):
        self.api_key = api_key
        self.base_url = "http://api.openweathermap.org/data/2.5/weather"
        self.forecast_url = "http://api.openweathermap.org/data/2.5/forecast"
        self.city = city or "Austin"
        self.logger = logging.getLogger(__name__)
        self.cache_ttl = max(cache_ttl_seconds, 60)
        self._current_cache: Optional[Dict[str, Any]] = None
        self._current_cached_at: Optional[datetime] = None
        self._forecast_cache: List[Dict[str, Any]] = []
        self._forecast_cached_at: Optional[datetime] = None

    def _is_cache_stale(self, cached_at: Optional[datetime]) -> bool:
        if not cached_at:
            return True
        return datetime.utcnow() - cached_at > timedelta(seconds=self.cache_ttl)

    def get_current_weather(self):
        if self._current_cache and not self._is_cache_stale(self._current_cached_at):
            return self._current_cache

        params = {
            "q": self.city,
            "appid": self.api_key,
            "units": "imperial",
        }

        try:
            response = requests.get(self.base_url, params=params, timeout=10)
            response.raise_for_status()
            self._current_cache = response.json()
            self._current_cached_at = datetime.utcnow()
            return self._current_cache
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error fetching weather data: {e}")
            return self._current_cache

    def get_multi_day_forecast(self, days: int = 3):
        if (
            self._forecast_cache
            and not self._is_cache_stale(self._forecast_cached_at)
            and len(self._forecast_cache) >= days
        ):
            return self._forecast_cache[:days]

        params = {
            "q": self.city,
            "appid": self.api_key,
            "units": "imperial",
        }
        try:
            response = requests.get(self.forecast_url, params=params, timeout=10)
            response.raise_for_status()
        except requests.exceptions.RequestException as exc:
            self.logger.error("Error fetching weather forecast: %s", exc)
            return self._forecast_cache[:days]

        payload = response.json()
        entries = payload.get("list") or []
        grouped = defaultdict(list)
        for entry in entries:
            dt_value = entry.get("dt")
            if dt_value is None:
                continue
            entry_time = datetime.utcfromtimestamp(dt_value)
            grouped[entry_time.date()].append(entry)

        forecasts = []
        today = datetime.utcnow().date()
        future_dates = [
            date_key for date_key in sorted(grouped.keys()) if date_key > today
        ]
        for date_key in future_dates[:days]:
            day_entries = grouped[date_key]
            temps = [item["main"]["temp"] for item in day_entries if "main" in item]
            if not temps:
                continue
            high = max(temps)
            low = min(temps)
            icons = [
                item["weather"][0]["icon"]
                for item in day_entries
                if item.get("weather")
            ]
            icon = icons and Counter(icons).most_common(1)[0][0]
            forecasts.append(
                {
                    "day": datetime.combine(date_key, datetime.min.time()).strftime(
                        "%a"
                    ),
                    "high": high,
                    "low": low,
                    "icon": icon,
                }
            )
        self._forecast_cache = forecasts
        self._forecast_cached_at = datetime.utcnow()
        return forecasts[:days]

    def last_forecast_refresh(self) -> Optional[str]:
        if not self._forecast_cached_at:
            return None
        return self._forecast_cached_at.strftime("%H:%M")

    def get_weather_icon(self, icon_code):
        icon_url = f"https://openweathermap.org/img/wn/{icon_code}@2x.png"
        try:
            response = requests.get(icon_url, timeout=10)
            response.raise_for_status()
            icon_image = Image.open(BytesIO(response.content))
            return icon_image
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error fetching weather icon: {e}")
            return None
