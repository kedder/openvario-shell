from typing import List, Tuple

import urwid


class UrwidMock:
    def render(self, w: urwid.Widget) -> str:
        canvas = w.render(self._get_size(w))
        contents = [t.decode("utf-8") for t in canvas.text]
        return "\n".join(contents)

    def keypress(self, w: urwid.Widget, keys: List[str]) -> None:
        for key in keys:
            nothandled = w.keypress(self._get_size(w), key)
            assert nothandled is None

    def _get_size(self, w: urwid.Widget) -> Tuple[int, ...]:
        size: Tuple[int, ...] = (60, 40)
        if "flow" in w.sizing():
            size = (60,)
        return size
