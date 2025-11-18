import logging
import os
from typing import Optional

import requests


class Stock:
    """Thin AlphaVantage client for a single symbol."""

    def __init__(self, api_key: str, stock_symbol: str):
        self.api_key = api_key
        self.stock_symbol = stock_symbol
        self.logger = logging.getLogger(__name__)
        logging.basicConfig(level=logging.INFO)

    def get_stock_info(self) -> Optional[dict]:
        """Fetch the latest quote data with timeouts and error handling."""
        url = (
            "https://www.alphavantage.co/query"
            f"?function=GLOBAL_QUOTE&symbol={self.stock_symbol}&apikey={self.api_key}"
        )

        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
        except requests.RequestException as exc:
            self.logger.error("AlphaVantage request failed for %s: %s", self.stock_symbol, exc)
            return None

        parsed_data = data.get('Global Quote')
        if not parsed_data:
            self.logger.warning("No Global Quote payload returned for %s", self.stock_symbol)
            return None

        try:
            return {
                'symbol': parsed_data['01. symbol'],
                'price': float(parsed_data['05. price']),
                'change': float(parsed_data['09. change']),
                'percent_change': parsed_data['10. change percent']
            }
        except (KeyError, ValueError) as exc:
            self.logger.error("Incomplete AlphaVantage data for %s: %s", self.stock_symbol, exc)
            return None

    def get_stock_icon_path(self):
        current_dir = os.path.dirname(__file__)  # Get the directory where the script is located
        stock_images_dir = os.path.join(current_dir, 'StockImages')  # Construct the path to StockImages
        return os.path.join(stock_images_dir, f"{self.stock_symbol}.png")

