from typing import Any, Callable, Dict


class Renderer:
    """
    Thin wrapper around RGBMatrix double buffering that skips redraws when
    successive frames are identical. For animated panels, pass force=True.
    """

    def __init__(self, matrix, logger=None):
        self.matrix = matrix
        self.logger = logger
        self._signatures: Dict[str, Any] = {}

    def render(
        self,
        key: str,
        signature: Any,
        draw_fn: Callable[[Any], None],
        *,
        force: bool = False,
    ) -> bool:
        if not force and self._signatures.get(key) == signature:
            return False

        canvas = self.matrix.CreateFrameCanvas()
        draw_fn(canvas)
        self.matrix.SwapOnVSync(canvas)
        self._signatures[key] = signature
        if self.logger:
            self.logger.debug("Rendered frame for %s", key)
        return True
