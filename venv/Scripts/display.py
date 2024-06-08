import time
from datetime import datetime, time as dtime
import logging
from weather_display import WeatherDisplay
from glucose_display import GlucoseDisplay
from stocks_display import StockDisplay
from RGBMatrixEmulator import RGBMatrix, RGBMatrixOptions, graphics
import schedule


class DisplayManager:
    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.weather_display = WeatherDisplay(config)
        self.glucose_display = GlucoseDisplay(config)
        self.stock_display = StockDisplay(config)
        self.display_index = 0
        self.matrix = self.setup_matrix()
        self.sleep_duration = 5  # Initial sleep duration
        self.display_durations = [60, 60, 10]  # Durations for glucose, weather, and stock display

    def setup_matrix(self):
        options = RGBMatrixOptions()
        options.rows = 32
        options.cols = 64
        options.chain_length = 1
        options.parallel = 1
        options.hardware_mapping = 'adafruit-hat'
        return RGBMatrix(options=options)

    def get_current_datetime(self):
        now = datetime.now()
        formatted_date = now.strftime("%b %d")
        formatted_time = now.strftime("%I:%M %p")
        formatted_datetime = f"{formatted_date} {formatted_time}"
        return formatted_datetime

    def is_market_closed(self):
        now = datetime.now().time()
        market_close_time = dtime(16, 0)  # Assuming market closes at 4 PM
        return now >= market_close_time

    def fetch_stock_data_on_market_close(self):
        if self.is_market_closed():
            self.stock_display.stock_data_table = self.stock_display.fetch_all_stock_info()
            self.logger.info("Stock data updated after market close")

    def display_text(self, canvas, font, x, y, color, text):
        graphics.DrawText(canvas, font, x, y, color, text)

    def run(self):
        font_small = graphics.Font()
        font_small.LoadFont("4x6.bdf")  # Use a smaller font

        font_large = graphics.Font()
        font_large.LoadFont("5x8.bdf")

        # Schedule the task to run when the stock market closes (e.g., 4 PM EST)
        schedule.every().day.at("16:00").do(self.fetch_stock_data_on_market_close)

        while True:
            canvas = self.matrix.CreateFrameCanvas()
            # Get current date and time
            current_datetime = self.get_current_datetime()

            # Display date and time at the top of the screen
            self.display_text(
                canvas, font_small, 2, 8, graphics.Color(
                    255, 165, 0), current_datetime)

            if self.display_index == 0:
                # Display glucose data
                self.glucose_display.display(canvas, font_large, font_small)
                self.sleep_duration = self.display_durations[0]
            elif self.display_index == 1:
                # Display weather data
                self.weather_display.display(canvas, font_large)
                self.sleep_duration = self.display_durations[1]
            elif self.display_index == 2:
                # Display stock data
                self.stock_display.display(canvas, font_small)
                self.sleep_duration = self.display_durations[2]

                # Check if all stocks have been displayed
                if self.stocks_displayed_count >= len(self.stock_display.stock_data_table):
                    self.stocks_displayed_count = 0  # Reset counter
                    self.display_index = (self.display_index + 1) % 3  # Rotate to the next display


            # Update the LED matrix
            canvas = self.matrix.SwapOnVSync(canvas)
            time.sleep(self.sleep_duration)  # Sleep for configured duration

            # Rotate display index
            self.display_index = (self.display_index + 1) % 3  # Rotate between 0, 1, and 2

            # Run scheduled tasks
            schedule.run_pending()

# Run the DisplayManager
if __name__ == "__main__":
    display_manager = DisplayManager(config)
    display_manager.run()
