from ..matrix.helper import graphics


class BaseDisplay:
    """Shared helpers for drawing text and clearing the LED canvas."""

    def draw_text(self, canvas, font, x, y, color, text):
        """Draw text and return the x coordinate following the rendered string."""
        return graphics.DrawText(canvas, font, x, y, color, text)

    def draw_text_with_shadow(self, canvas, font, x, y, fg_color, shadow_color, text, offset=(1, 1)):
        """Draw text with a shadow to increase contrast/crispness.

        Draws a shadow at `x+offset[0], y+offset[1]` using `shadow_color`,
        then draws the foreground text at `x, y` using `fg_color`.
        Returns the x coordinate following the rendered foreground string.
        """
        # draw shadow first (offset by 1,1 by default)
        try:
            graphics.DrawText(canvas, font, x + offset[0], y + offset[1], shadow_color, text)
        except Exception:
            # best-effort: ignore shadow drawing errors and still draw fg text
            pass
        return graphics.DrawText(canvas, font, x, y, fg_color, text)
    def clear_canvas(self, canvas):
        canvas.Clear()
