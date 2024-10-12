# Dexcom and LED Matrix Display Project

## Overview
This project integrates real-time glucose monitoring, weather data, and stock market updates into an RGB LED matrix display. Glucose readings are fetched using the Dexcom API, while weather and stock data are retrieved from external APIs. The display cycles through glucose, weather, and stock information.

## Files
1. **`glucose.py`**: Manages glucose data retrieval using `pydexcom`.
2. **`DisplayManager.py`**: Handles the display of glucose, weather, and stock data on the LED matrix.
3. **`stocks_display.py`**: Fetches and displays stock market data.
4. **`weather_display.py`**: Fetches and displays current weather updates.

## Requirements
- `pydexcom`
- `schedule`
- `RGBMatrixEmulator`
- `Pillow` (for image processing)

## Usage
1. Set up your API keys for Dexcom, weather, and stocks in a `config.json` file.
2. Run `DisplayManager.py` to start the display loop, showing glucose, weather, and stock updates on the matrix.

## Features
- **Glucose Monitoring**: Displays real-time glucose levels and trends from Dexcom.
- **Weather Display**: Shows current temperature and weather icon.
- **Stock Market Updates**: Displays stock prices with percentage changes and color-coded trends.

## Notes
- Designed for use with an Adafruit RGB Hat LED matrix.
- Customize stock symbols in `StockDisplay.py` for personal preferences.

