from typing import List, Tuple, Dict, Coroutine
from dataclasses import dataclass
import asyncio
import functools

import urwid
from urwid import signals

from ovshell.protocol import ScreenManager, Activity
from ovshell import widget
from ovshell import protocol


@dataclass
class ActivityContext:
    activity: protocol.Activity
    widget: urwid.Widget
    palette: Dict[str, Tuple]
    tasks: List[asyncio.Task]


class TopBar(urwid.WidgetWrap):
    def __init__(self) -> None:
        w = urwid.Text("Openvario")
        super().__init__(urwid.AttrMap(w, "topbar"))


class FooterBar(urwid.WidgetPlaceholder):
    def __init__(self) -> None:
        super().__init__(urwid.AttrMap(urwid.Divider(), "bg"))


class ScreenManagerImpl(ScreenManager):
    _header: TopBar
    _footer: FooterBar
    _main_view: urwid.WidgetPlaceholder

    def __init__(self, mainloop: urwid.MainLoop) -> None:
        self._mainloop = mainloop
        self._main_view = urwid.WidgetPlaceholder(urwid.SolidFill(" "))
        self.layout = self._create_layout()
        self._act_stack: List[ActivityContext] = []

        self._mainloop.widget = self.layout

    def _create_layout(self) -> urwid.Widget:
        btxt = urwid.BigText("Openvario", urwid.font.Thin6x6Font())
        splash = urwid.Filler(urwid.Padding(btxt, "center", "clip"), "middle")
        self._main_view.original_widget = splash
        self._header = TopBar()
        self._footer = FooterBar()
        return urwid.Frame(
            self._main_view,
            header=self._header,
            footer=urwid.AttrMap(self._footer, "bg"),
        )

    def push_activity(self, activity: Activity, palette: List[Tuple] = None) -> None:
        self._hide_shown_activity()

        w = activity.create()
        signals = widget.KeySignals(urwid.AttrMap(w, widget.NORMAL_ATTR_MAP))
        urwid.connect_signal(
            signals, "cancel", self._cancel_activity, user_args=[activity]
        )
        if palette is not None:
            self._mainloop.screen.register_palette(palette)
            self._mainloop.screen.clear()
        self._main_view.original_widget = signals
        self._act_stack.append(
            ActivityContext(activity, signals, palette=self._get_palette(), tasks=[])
        )
        activity.activate()
        activity.show()

    def push_modal(self, activity: Activity, options: protocol.ModalOptions) -> None:
        self._hide_shown_activity()

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
        self._act_stack.append(
            ActivityContext(activity, modal, palette=self._get_palette(), tasks=[])
        )
        activity.activate()
        activity.show()

    def pop_activity(self) -> None:
        curactctx = self._act_stack.pop()
        for task in curactctx.tasks:
            task.cancel()
        curactctx.activity.hide()
        curactctx.activity.destroy()

        prevactctx = self._act_stack[-1]
        self._main_view.original_widget = prevactctx.widget
        self._reset_palette(prevactctx.palette)
        prevactctx.activity.show()

    def set_status(self, text: protocol.UrwidText):
        self._footer.original_widget = urwid.Text(text)

    def spawn_task(self, activity: Activity, coro: Coroutine) -> asyncio.Task:
        # Find activity context for given activity
        for actx in reversed(self._act_stack):
            if actx.activity is activity:
                break
        else:
            raise RuntimeError("Activity is not started")

        task = asyncio.create_task(coro)

        done_callback = functools.partial(self._task_done, actx)
        task.add_done_callback(done_callback)
        actx.tasks.append(task)
        return task

    def _cancel_activity(self, activity: Activity, w: urwid.Widget) -> None:
        self.pop_activity()

    def _hide_shown_activity(self) -> None:
        if not self._act_stack:
            return

        topact_ctx = self._act_stack[-1]
        topact_ctx.activity.hide()

    def _get_palette(self) -> Dict[str, Tuple]:
        return self._mainloop.screen._palette.copy()

    def _reset_palette(self, palette: Dict[str, Tuple]):
        # Reset the palette for activity. We use a bit of urwid implementation
        # details here, because of lack of public way to do this.
        self._mainloop.screen._palette = palette.copy()
        for name, entry in palette.items():
            (basic, mono, high_88, high_true) = entry
            signals.emit_signal(
                self._mainloop.screen,
                urwid.UPDATE_PALETTE_ENTRY,
                name,
                basic,
                mono,
                high_88,
                high_true,
            )
        self._mainloop.screen.clear()

    def _task_done(self, actx: ActivityContext, task: asyncio.Task) -> None:
        actx.tasks.remove(task)
        if task.cancelled():
            return
        exc = task.exception()
        if exc is not None:
            msg = f"Task failed. {exc.__class__.__name__}: {exc}"
            self.set_status(("error message", msg))
            return
