import requests
import logging  # Import the logging module
from PIL import Image
import time
import os


class Stock:
    def __init__(self, api_key, stock_symbol):
        self.api_key = api_key
        self.stock_symbol = stock_symbol
        self.logger = logging.getLogger(__name__)
        logging.basicConfig(level=logging.INFO)

    def get_stock_info(self):
        url = f'https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={self.stock_symbol}&apikey={self.api_key}'
        response = requests.get(url)

        if response.status_code == 200:
            data = response.json()
            parsed_data = data.get('Global Quote')
            if parsed_data:
                return {
                    'symbol': parsed_data['01. symbol'],
                    'price': float(parsed_data['05. price']),
                    'change': float(parsed_data['09. change']),
                    'percent_change': parsed_data['10. change percent']
                }

        return None

    def get_stock_icon_path(self):
        return  f"C:\\Users\\krjam\\OneDrive\\Documents\\Stock Images\\{self.stock_symbol}.png"


