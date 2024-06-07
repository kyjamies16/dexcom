# weather.py
import requests
from PIL import Image
from io import BytesIO
import logging

class Weather:
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = 'http://api.openweathermap.org/data/2.5/weather'
        self.city = 'Austin'  # Default city
        self.logger = logging.getLogger(__name__)

    def get_current_weather(self):
        params = {
            'q': self.city,
            'appid': self.api_key,
            'units': 'imperial',
        }

        try:
            response = requests.get(self.base_url, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error fetching weather data: {e}")
            return None

    def get_weather_icon(self, icon_code):
        icon_url = f"https://openweathermap.org/img/wn/{icon_code}@2x.png"
        try:
            response = requests.get(icon_url)
            response.raise_for_status()
            icon_image = Image.open(BytesIO(response.content))
            return icon_image
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error fetching weather icon: {e}")
            return None