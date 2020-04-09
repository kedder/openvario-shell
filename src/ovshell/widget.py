import urwid

class PlainButton(urwid.Button):
    def __init__(self, text: str) -> None:
        super().__init__(text)
        txt = urwid.SelectableIcon(text)
        txt.align = "center"
        btn = urwid.AttrWrap(txt, "btn normal", "btn focus")
        self._w = btn


class SelectableListItem(urwid.Button):
    def __init__(self, text: str) -> None:
        super().__init__(text)
        btn = urwid.SelectableIcon(text)
        wdg = urwid.AttrMap(btn, "li normal", "li focus")
        self._w = wdg

    def _btnclicked(self, btn):
        self._emit("selected")
