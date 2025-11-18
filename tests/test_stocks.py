import configparser
import types

import pytest
import requests

from app.services.stocks import Stock
from app.displays.stocks import StockDisplay
from app.services import stocks as stocks_service_module
from app.displays import stocks as stocks_display_module


def build_config():
    config = configparser.ConfigParser()
    config["Stock"] = {
        "api_key": "demo",
        "request_interval_seconds": "0",
    }
    return config


def test_stock_get_info_success(monkeypatch):
    payload = {
        "Global Quote": {
            "01. symbol": "TEST",
            "05. price": "123.45",
            "09. change": "1.23",
            "10. change percent": "1.00%",
        }
    }

    class DummyResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return payload

    monkeypatch.setattr(stocks_service_module.requests, "get", lambda *_, **__: DummyResponse())

    stock = Stock("key", "TEST")
    actual = stock.get_stock_info()

    assert actual == {
        "symbol": "TEST",
        "price": 123.45,
        "change": 1.23,
        "percent_change": "1.00%",
    }


def test_stock_get_info_handles_request_errors(monkeypatch):
    def fake_get(*_, **__):
        raise requests.RequestException("network down")

    monkeypatch.setattr(stocks_service_module.requests, "get", fake_get)

    stock = Stock("key", "TEST")
    assert stock.get_stock_info() is None


def test_stock_display_draws_expected_text(monkeypatch):
    # Avoid slow API refresh during __init__
    monkeypatch.setattr(StockDisplay, "refresh_stock_data", lambda self: None)
    monkeypatch.setattr(StockDisplay, "async_refresh_stock_data", lambda self: None)
    config = build_config()
    display = StockDisplay(config)
    display.stock_data_table = [{
        "symbol": "DEMO",
        "price": 123.456,
        "change": 1.0,
        "percent_change": "0.80%",
    }]
    drawn = []

    def fake_draw(self, canvas, font, x, y, color, text):
        drawn.append((x, y, text))
        return x + len(text)

    display.draw_text = types.MethodType(fake_draw, display)
    display._measure_text = lambda font, text: len(text)

    class FakeCanvas:
        def __init__(self):
            self.cleared = False

        def Clear(self):
            self.cleared = True

    canvas = FakeCanvas()

    monkeypatch.setattr(stocks_display_module, "format_display_datetime", lambda: "HEADER")

    display.display(canvas, font_small=object())

    assert canvas.cleared is True
    assert [text for *_xy, text in drawn] == ["HEADER", "DEMO", ": ", "0.80%"]
