import logging
import time
from datetime import datetime, timedelta, time as dtime
import schedule
from rgbmatrix import RGBMatrix, RGBMatrixOptions, graphics

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
        self.display_durations = [60, 60, 15]
        self.current_stock_index = 0
        self.showing_stocks = False
        self.stock_display_end_time = None

    def setup_matrix(self):
        options = RGBMatrixOptions()
        options.rows = 32
        options.cols = 64
        options.chain_length = 1
        options.parallel = 1
        options.hardware_mapping = 'adafruit-hat'
        options.brightness = 50
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
            self.stock_display.save_stock_info_to_file()
            self.logger.info("Stock data updated after market close")
            self.showing_stocks = True
            self.stock_display_end_time = datetime.now() + timedelta(hours=1)

    def display_text(self, canvas, font, x, y, color, text):
        graphics.DrawText(canvas, font, x, y, color, text)

    def run(self):
        font_small = graphics.Font()
        font_small.LoadFont("4x6.bdf")  # Use a smaller font

        font_large = graphics.Font()
        font_large.LoadFont("5x8.bdf")

        # Schedule the task to run when the stock market closes (e.g., 4 PM)
        schedule.every().day.at("16:00").do(self.fetch_stock_data_on_market_close)

        while True:
            canvas = self.matrix.CreateFrameCanvas()
            # Get current date and time
            current_datetime = self.get_current_datetime()

            # Display date and time at the top of the screen
            self.display_text(
                canvas, font_small, 2, 8, graphics.Color(255, 165, 0), current_datetime)

            now = datetime.now()

            if self.showing_stocks and now < self.stock_display_end_time:
                # Display stock data
                if self.current_stock_index < len(self.stock_display.stock_data_table):
                    self.stock_display.current_stock_index = self.current_stock_index
                    self.stock_display.display(canvas, font_small)
                    self.sleep_duration = self.display_durations[2]
                    self.current_stock_index += 1
                    self.logger.info(
                        f"Displaying stock data for index {self.current_stock_index}")
                else:
                    # All stocks displayed, reset for next cycle
                    self.current_stock_index = 0
                    self.logger.info(
                        "All stocks displayed, continuing stock display within the hour")
            else:
                # Display other data
                if self.display_index == 0:
                    # Display glucose data
                    self.glucose_display.display(canvas, font_large, font_small)
                    self.sleep_duration = self.display_durations[0]
                    self.display_index += 1
                    self.logger.info("Displaying glucose data")
                elif self.display_index == 1:
                    # Display weather data
                    self.weather_display.display(canvas, font_large)
                    self.sleep_duration = self.display_durations[1]
                    self.display_index += 1
                    self.logger.info("Displaying weather data")
                else:
                    # Reset display index
                    self.display_index = 0

            # Update the LED matrix
            canvas = self.matrix.SwapOnVSync(canvas)
            time.sleep(self.sleep_duration)  # Sleep for configured duration

            # Run scheduled tasks
            schedule.run_pending()



# Run the DisplayManager
if __name__ == "__main__":
    display_manager = DisplayManager(config)
    display_manager.run()
