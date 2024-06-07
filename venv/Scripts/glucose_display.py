# glucose_display.py
from blood_glucose import Glucose
from RGBMatrixEmulator import graphics


class GlucoseDisplay:
    def __init__(self, config):
        self.glucose = Glucose(config["Dexcom"]["username"], config["Dexcom"]["password"])

    # Initialize RGB matrix, load fonts, etc.
    def display(self, canvas, font_large, font_small):
        glucose_reading = self.glucose.get_glucose_reading()
        if glucose_reading:
            glucose_trend = self.glucose.get_glucose_trend()
            glucose_value = self.glucose.get_glucose_value()

            # Determine text color based on glucose reading
            if glucose_value <= self.glucose.low_value:
                text_color = graphics.Color(255, 0, 0)
            elif self.glucose.low_value < glucose_value <= self.glucose.high_value:
                text_color = graphics.Color(0, 255, 0)
            else:
                text_color = graphics.Color(255, 255, 0)

            # Display glucose reading in the center
            glucose_text = f"{glucose_value} {glucose_trend} mg/dl"
            x = 4
            y = 22
            graphics.DrawText(canvas, font_large, x, y, text_color, glucose_text)
        else:
            # Display "No Readings" if there is no glucose reading
            x = 4
            y = 22
            graphics.DrawText(canvas, font_small, x, y, graphics.Color(255, 255, 255), "No Readings")
