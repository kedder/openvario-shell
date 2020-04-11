from typing import List, Tuple

import urwid

from ovshell.protocol import ScreenManager, Activity, OpenVarioShell
from ovshell import widget


class ScreenManagerImpl(ScreenManager):
    def __init__(self) -> None:
        self._main_view = urwid.WidgetPlaceholder(urwid.SolidFill(" "))
        self.layout = self._create_layout()
        self._act_stack: List[Tuple[Activity, urwid.Widget]] = []

    def _create_layout(self) -> urwid.Widget:
        btxt = urwid.BigText("Openvario", urwid.font.Thin6x6Font())
        splash = urwid.Filler(urwid.Padding(btxt, "center", "clip"), "middle")
        self._main_view.original_widget = splash
        return urwid.Frame(
            self._main_view, header=urwid.Text("Header"), footer=urwid.Text("Footer")
        )

    def push_activity(self, activity: Activity) -> None:
        w = activity.create()
        signals = widget.KeySignals(w)
        urwid.connect_signal(
            signals, "cancel", self._cancel_activity, user_args=[activity]
        )
        self._main_view.original_widget = signals
        activity.activate()
        self._act_stack.append((activity, signals))

    def pop_activity(self) -> None:
        oldact, oldw = self._act_stack.pop()
        oldact.destroy()

        newact, curw = self._act_stack[-1]
        self._main_view.original_widget = curw
        newact.activate()

    def _cancel_activity(self, activity: Activity, w: urwid.Widget) -> None:
        self.pop_activity()


class OpenvarioShellImpl(OpenVarioShell):
    def __init__(self, screen: ScreenManager) -> None:
        self.screen = screen
        self.devices = None
        self.processes = None
