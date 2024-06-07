# glucose.py
from pydexcom import Dexcom

class Glucose:
    def __init__(self, username, password):
        self.dexcom = Dexcom(username=username, password=password)
        self.high_value = 200
        self.low_value = 70

    def get_glucose_reading(self):
        try:
            return self.dexcom.get_current_glucose_reading()
        except Exception as e:
            # Handle specific exception types if available
            raise RuntimeError("Error fetching glucose reading") from e

    def get_glucose_trend(self):
        try:
            return self.dexcom.get_current_glucose_reading().trend_arrow
        except Exception as e:
            raise RuntimeError("Error fetching glucose trend") from e

    def get_glucose_value(self):
        try:
            return self.dexcom.get_current_glucose_reading().mg_dl
        except Exception as e:
            raise RuntimeError("Error fetching glucose value") from e