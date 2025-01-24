# weather_display.py
from weather import Weather
from rgbmatrix import RGBMatrix, graphics

class WeatherDisplay:
    def __init__(self, config):
        self.weather = Weather(config["Weather"]["api_key"])

    def display(self, canvas, font_large):
        weather_data = self.weather.get_current_weather()
        if weather_data:
            temperature = weather_data['main']['temp']
            # description = weather_data['weather'][0]['description'].title()
            weather_text = f"{int(temperature)}°F"

            # Display weather information
            x_weather = 32
            y_weather = 24
            graphics.DrawText(canvas, font_large, x_weather, y_weather,
                              graphics.Color(255, 255, 255), weather_text)

            # Get and display weather icon
            weather_icon_code = weather_data['weather'][0]['icon']
            weather_icon = self.weather.get_weather_icon(weather_icon_code)

            if weather_icon:
                weather_icon.thumbnail((22, 18))
                canvas.SetImage(weather_icon.convert('RGB'), 8, 10)
        else:
            # Display "No weather data available" if there is no weather data
            x_weather = 22
            y_weather = 22
            graphics.DrawText(canvas, font_large, x_weather, y_weather,
                              graphics.Color(255, 255, 255), "N/A")
