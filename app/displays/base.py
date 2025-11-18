from ..matrix.helper import graphics


class BaseDisplay:
    """Shared helpers for drawing text and clearing the LED canvas."""

    def draw_text(self, canvas, font, x, y, color, text):
        """Draw text and return the x coordinate following the rendered string."""
        return graphics.DrawText(canvas, font, x, y, color, text)

    def clear_canvas(self, canvas):
        canvas.Clear()
