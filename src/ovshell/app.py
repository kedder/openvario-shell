from typing import List, Tuple, Iterable, cast
import pkg_resources

import urwid

from ovshell.protocol import ScreenManager, Activity, OpenVarioShell
from ovshell.protocol import Extension, ExtensionFactory
from ovshell import widget
from ovshell import protocol
from ovshell import settings


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
        signals = widget.KeySignals(urwid.AttrMap(w, widget.NORMAL_ATTR_MAP))
        urwid.connect_signal(
            signals, "cancel", self._cancel_activity, user_args=[activity]
        )
        self._main_view.original_widget = signals
        activity.activate()
        self._act_stack.append((activity, signals))

    def push_modal(self, activity: Activity, options: protocol.ModalOptions) -> None:
        bg = self._main_view.original_widget
        modal_w = activity.create()
        modal_w = urwid.AttrMap(modal_w, widget.LIGHT_ATTR_MAP)
        signals = widget.KeySignals(modal_w)
        urwid.connect_signal(
            signals, "cancel", self._cancel_activity, user_args=[activity]
        )
        modal = urwid.Overlay(
            signals,
            bg,
            align=options.align,
            width=options.width,
            valign=options.valign,
            height=options.height,
            min_width=options.min_width,
            min_height=options.min_height,
            left=options.left,
            right=options.right,
            top=options.top,
            bottom=options.bottom,
        )
        self._main_view.original_widget = modal
        activity.activate()
        self._act_stack.append((activity, modal))

    def pop_activity(self) -> None:
        oldact, oldw = self._act_stack.pop()
        oldact.destroy()

        newact, curw = self._act_stack[-1]
        self._main_view.original_widget = curw
        newact.activate()

    def _cancel_activity(self, activity: Activity, w: urwid.Widget) -> None:
        self.pop_activity()


class ExtensionManagerImpl(protocol.ExtensionManager):
    _extensions: List[Extension]

    def __init__(self):
        self._extensions = []

    def load_all(self, app: OpenVarioShell) -> None:
        for entry_point in pkg_resources.iter_entry_points("ovshell.extensions"):
            extfactory = cast(ExtensionFactory, entry_point.load())
            ext = extfactory(entry_point.name, app)
            self._extensions.append(ext)
            print(f"Loaded extension: {ext.title}")

    def list_extensions(self) -> Iterable[Extension]:
        return self._extensions


class OpenvarioShellImpl(OpenVarioShell):
    def __init__(self, screen: ScreenManager, settings_fname: str) -> None:
        self.screen = screen
        self.settings = settings.StoredSettingsImpl.load(settings_fname)
        self.devices = None
        self.processes = None
        self.extensions = ExtensionManagerImpl()

    def quit(self) -> None:
        raise urwid.ExitMainLoop()
