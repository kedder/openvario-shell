import urwid

NORMAL_ATTR_MAP = {None: "bg"}
LIGHT_ATTR_MAP = {None: "bg light", "bg": "bg light", "li normal": "li normal light"}


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


class ActivityHeader(urwid.WidgetWrap):
    def __init__(self, title: str) -> None:
        w = urwid.Text("  " + title)
        w = urwid.AttrMap(
            urwid.Pile(
                [
                    urwid.Divider(),
                    w,
                    urwid.Divider(),
                    urwid.AttrMap(
                        urwid.Divider("\N{MEDIUM SHADE}"), "screen header divider"
                    ),
                ]
            ),
            "screen header",
        )

        super().__init__(urwid.Pile([w, urwid.Divider()]))


class KeySignals(urwid.WidgetWrap):
    signals = ["cancel", "menu"]
    signal_map = {
        "esc": "cancel",
        "f1": "menu",
    }

    def __init__(self, widget):
        super().__init__(widget)

    def keypress(self, size, key):
        unhandled = key

        # Widgets that are not selectable might not be able to handle
        # keypresses
        if self._w.selectable():
            unhandled = self._w.keypress(size, key)

        if not unhandled:
            return
        if key in self.signal_map:
            self._emit(self.signal_map[key])
            return
        return key

    def selectable(self):
        # We need this widget to be selectable in order to receive keypresses
        return True
