# weather.py
import logging
from collections import Counter, defaultdict
from datetime import datetime
from io import BytesIO
from typing import Any, Dict, List, Optional

import requests
from PIL import Image

from ..utils.cache import DataCache


class Weather:
    def __init__(
        self,
        api_key: str,
        city: str = "Austin",
        cache: Optional[DataCache] = None,
        current_ttl_seconds: int = 600,
        forecast_ttl_seconds: int = 900,
    ):
        self.api_key = api_key
        self.base_url = "http://api.openweathermap.org/data/2.5/weather"
        self.forecast_url = "http://api.openweathermap.org/data/2.5/forecast"
        self.city = city or "Austin"
        self.logger = logging.getLogger(__name__)
        self.cache = cache or DataCache(logger=self.logger)
        self.current_ttl = max(current_ttl_seconds, 60)
        self.forecast_ttl = max(forecast_ttl_seconds, 120)
        self._forecast_cached_at: Optional[datetime] = None
        self._icon_cache: Dict[str, Image.Image] = {}

    def get_current_weather(self):
        return self.cache.get(
            f"weather:{self.city}:current",
            self._fetch_current_weather,
            ttl_seconds=self.current_ttl,
            allow_stale=True,
        )

    def _fetch_current_weather(self):
        params = {"q": self.city, "appid": self.api_key, "units": "imperial"}
        try:
            response = requests.get(self.base_url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as exc:
            self.logger.error("Error fetching weather data: %s", exc)
            return None

    def get_multi_day_forecast(self, days: int = 3):
        def _fetch():
            payload = self._fetch_forecast_payload()
            return self._parse_forecast_payload(payload)

        forecast = self.cache.get(
            f"weather:{self.city}:forecast",
            _fetch,
            ttl_seconds=self.forecast_ttl,
            allow_stale=True,
        )
        return (forecast or [])[:days]

    def _fetch_forecast_payload(self):
        params = {"q": self.city, "appid": self.api_key, "units": "imperial"}
        try:
            response = requests.get(self.forecast_url, params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as exc:
            self.logger.error("Error fetching weather forecast: %s", exc)
            return None

    def _parse_forecast_payload(self, payload: Optional[Dict[str, Any]]):
        if not payload:
            return []
        local_tz = datetime.now().astimezone().tzinfo
        entries = payload.get("list") or []
        grouped = defaultdict(list)
        for entry in entries:
            dt_value = entry.get("dt")
            if dt_value is None:
                continue
            utc_time = datetime.utcfromtimestamp(dt_value)
            entry_time = utc_time.astimezone(local_tz) if local_tz else utc_time
            grouped[entry_time.date()].append(entry)

        forecasts = []
        today = datetime.now(local_tz).date() if local_tz else datetime.utcnow().date()
        future_dates = [
            date_key for date_key in sorted(grouped.keys()) if date_key > today
        ]
        for date_key in future_dates[:3]:
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
        self._forecast_cached_at = datetime.utcnow()
        return forecasts

    def last_forecast_refresh(self) -> Optional[str]:
        if not self._forecast_cached_at:
            return None
        return self._forecast_cached_at.strftime("%H:%M")

    def get_weather_icon(self, icon_code):
        if not icon_code:
            return None
        if icon_code in self._icon_cache:
            return self._icon_cache[icon_code]
        icon_url = f"https://openweathermap.org/img/wn/{icon_code}@2x.png"
        try:
            response = requests.get(icon_url, timeout=10)
            response.raise_for_status()
            icon_image = Image.open(BytesIO(response.content))
            self._icon_cache[icon_code] = icon_image
            return icon_image
        except requests.exceptions.RequestException as exc:
            self.logger.error("Error fetching weather icon: %s", exc)
            return None
