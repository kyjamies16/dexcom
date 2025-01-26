import os
import logging
import json
from PIL import ImageEnhance, Image
from datetime import datetime
from stocks import Stock


class StockDisplay:
    def __init__(self, config):
        self.api_key = config["Stock"]["api_key"]
        self.stock_symbols = ['COST','TSM', 'LEN', 'GOOG', 'VOO', 'CAT', 'DXCM', 'MSFT', 'AXP']
        self.stocks = [Stock(self.api_key, symbol) for symbol in self.stock_symbols]
        self.current_stock_index = 0
        self.logger = logging.getLogger(__name__)
        logging.basicConfig(level=logging.INFO)
        self.image_cache = {}

        # Fetch stock information once at initialization
        self.stock_data_table = self.fetch_all_stock_info()
        self.write_stock_data_to_file()

    def fetch_all_stock_info(self):
        stock_data_table = []
        for stock in self.stocks:
            stock_info = stock.get_stock_info()
            if stock_info:
                stock_icon_path = stock.get_stock_icon_path()
                stock_info['icon_path'] = stock_icon_path
                stock_data_table.append(stock_info)
        return stock_data_table

    def get_current_datetime(self):
        now = datetime.now()
        formatted_date = now.strftime("%b %d")
        formatted_time = now.strftime("%I:%M %p")
        formatted_datetime = f"{formatted_date} {formatted_time}"
        return formatted_datetime

    def enhance_image(self, image):
        if image.mode != 'RGB':
            image = image.convert('RGB')

        # Resize with high-quality downscaling
        image = image.resize((20, 18), Image.LANCZOS)

        # Increase sharpness
        sharpness_enhancer = ImageEnhance.Sharpness(image)
        image = sharpness_enhancer.enhance(3.0)  # Adjust sharpness as needed

        # Increase contrast
        contrast_enhancer = ImageEnhance.Contrast(image)
        image = contrast_enhancer.enhance(2.0)  # Adjust contrast as needed

        # Increase color saturation
        color_enhancer = ImageEnhance.Color(image)
        image = color_enhancer.enhance(2.0)  # Adjust color saturation as needed

        # Apply dithering if needed
        image = image.convert('RGB').convert('P', palette=Image.ADAPTIVE, dither=Image.FLOYDSTEINBERG)

        return image

    def get_enhanced_image(self, image_path):
        if image_path in self.image_cache:
            return self.image_cache[image_path]
        
        image = Image.open(image_path)
        enhanced_image = self.enhance_image(image)
        self.image_cache[image_path] = enhanced_image
        return enhanced_image

    def display(self, canvas, font_small):
        stock_data = self.stock_data_table[self.current_stock_index]
        canvas.Clear()
        self.logger.info(f"Displaying stock info: {stock_data}")
        
        # Display current date and time at the top of the display
        current_datetime = self.get_current_datetime()
        x_datetime = 2
        y_datetime = 8
        graphics.DrawText(canvas, font_small, x_datetime, y_datetime, graphics.Color(255, 165, 0), current_datetime)
        
        if stock_data:
            symbol = stock_data['symbol']
            price = "${:,.2f}".format(stock_data['price'])
            change = stock_data['change']
            percent_change_formatted = "{:.2f}%".format(float(stock_data['percent_change'].strip('%')))

            # Set color based on percent change
            if change > 0:
                percent_color = graphics.Color(0, 255, 0)  # Green
            elif change < 0:
                percent_color = graphics.Color(255, 0, 0)  # Red
            else:
                percent_color = graphics.Color(255, 255, 255)  # White

            stock_price = f"{price}"
            price_change = f"{percent_change_formatted}"

            # Display stock information
            x_price = 35
            y_price = 18
            graphics.DrawText(canvas, font_small, x_price, y_price, graphics.Color(255, 255, 255), stock_price) #white

            x_percent_change = 40
            y_percent_change = 28
            graphics.DrawText(canvas, font_small, x_percent_change, y_percent_change, percent_color, price_change)

            stock_image_path = stock_data.get('icon_path')
            if stock_image_path:
                stock_image = self.get_enhanced_image(stock_image_path)
                x_image = 5
                y_image = 12
                canvas.SetImage(stock_image.convert('RGB'), x_image, y_image)

        # Update to the next stock symbol for the next cycle
        self.current_stock_index = (self.current_stock_index + 1) % len(self.stock_data_table)

    def write_stock_data_to_file(self):
        file_path = "data/stock_data.json"
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w') as file:
            json.dump(self.stock_data_table, file)

    def read_stock_data_from_file(self):
        file_path = "data/stock_data.json"
        if not os.path.exists(file_path):
            return []
        with open(file_path, 'r') as file:
            stock_data_table = json.load(file)
        return stock_data_table

