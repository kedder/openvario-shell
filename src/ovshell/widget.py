import asyncio
from typing import Awaitable, Optional

import urwid

NORMAL_ATTR_MAP = {None: "bg"}
LIGHT_ATTR_MAP = {
    None: "bg light",
    "bg": "bg light",
    "li normal": "li normal light",
    "success message": "success message light",
    "error message": "error message light",
    "pg normal": "pg normal light",
}


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


class SelectableItem(urwid.WidgetWrap):
    signals = ["click"]

    def __init__(self, widget: urwid.Widget) -> None:
        wdg = urwid.AttrMap(widget, "li normal", "li focus")
        super().__init__(wdg)

    def selectable(self):
        return True

    def keypress(self, size, key: str) -> Optional[str]:
        if self._command_map[key] == "activate":
            self._emit("click")
            return None
        return key


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


class Waiting(urwid.WidgetWrap):
    _bullet = "\N{BLACK DIAMOND}"

    def __init__(self, size) -> None:
        self.size = size
        self.text = urwid.Text(" " * size)
        super().__init__(self.text)

    def start_waiting_for(self, awaitable: Awaitable[object]) -> None:
        asyncio.create_task(self.wait_for(awaitable))

    async def wait_for(self, awaitable: Awaitable[object]) -> object:
        waiting_task = asyncio.create_task(self.show_wait())
        try:
            return await awaitable
        finally:
            waiting_task.cancel()

    async def show_wait(self) -> None:
        self._w = urwid.AttrMap(self.text, "progress")
        try:
            return await self._run_show_wait()
        finally:
            self._w = self.text

    async def _run_show_wait(self) -> None:
        size = self.size
        forward = True
        while True:
            for n in range(size - 1):
                s = [" "] * size
                s[n if forward else size - 1 - n] = self._bullet
                self.text.set_text("".join(s))
                try:
                    await asyncio.sleep(0.2)
                finally:
                    # We're canceled
                    self.text.set_text(" " * size)
            forward = not forward
