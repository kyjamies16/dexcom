# matrix_helper.py
import logging

from ..config import load_config

logger = logging.getLogger(__name__)


config = load_config()
environment = config.get('Environment', 'name', fallback='prod').lower()


def _import_matrix_stack():
    """Best-effort import of the RGB matrix stack with graceful fallbacks."""
    try:
        if environment == 'dev':
            from RGBMatrixEmulator import RGBMatrix, RGBMatrixOptions, graphics  # type: ignore
            logger.info("Using RGBMatrixEmulator for development.")
            return RGBMatrix, RGBMatrixOptions, graphics
        from rgbmatrix import RGBMatrix, RGBMatrixOptions, graphics  # type: ignore
        logger.info("Using RGBMatrix for production.")
        return RGBMatrix, RGBMatrixOptions, graphics
    except Exception as exc:
        logger.warning("RGBMatrix modules unavailable (%s); using stub matrix.", exc)

        class _StubRGBMatrix:
            """Minimal stub to keep the app running without RGB hardware."""

            class Options:
                pass

            def __init__(self, *args, **kwargs):
                self.args = args
                self.kwargs = kwargs

            def CreateFrameCanvas(self):
                return self

            def Clear(self):
                return None

            def SetImage(self, *args, **kwargs):
                return None

            def SwapOnVSync(self, canvas):
                return canvas

        class _StubGraphics:
            @staticmethod
            def Color(r, g, b):
                return (r, g, b)

            class Font:
                def LoadFont(self, *_args, **_kwargs):
                    return None

            @staticmethod
            def DrawText(*_args, **_kwargs):
                return 0

        return _StubRGBMatrix, _StubRGBMatrix.Options, _StubGraphics


RGBMatrix, RGBMatrixOptions, graphics = _import_matrix_stack()


def initialize_matrix(options):
    return RGBMatrix(options=options)
