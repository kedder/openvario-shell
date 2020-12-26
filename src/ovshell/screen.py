import asyncio
import functools
from dataclasses import dataclass
from typing import Callable, Coroutine, Dict, List, Sequence, Tuple

import urwid
from urwid import signals

from ovshell import api, widget
from ovshell.api import Activity, IndicatorLocation, ScreenManager, UrwidText


@dataclass
class ActivityContext:
    activity: api.Activity
    widget: urwid.Widget
    palette: Dict[str, Tuple]
    tasks: List[asyncio.Task]


@dataclass
class TopIndicator:
    id: str
    markup: UrwidText
    location: IndicatorLocation
    weight: int


class TopBar(urwid.WidgetWrap):
    _indicators: Dict[str, TopIndicator]

    def __init__(self) -> None:
        self.left = urwid.Text("")
        self.right = urwid.Text("", align="right")
        self.cols = urwid.Columns([("pack", self.left), ("weight", 1, self.right)])
        self._indicators = {}
        super().__init__(urwid.AttrMap(self.cols, "topbar"))

    def set_indicator(
        self, iid: str, markup: UrwidText, location: IndicatorLocation, weight: int
    ) -> None:
        ind = TopIndicator(iid, markup, location, weight)
        self._indicators[iid] = ind
        self._invalidate()

    def remove_indicator(self, iid: str) -> None:
        self._dirty = True
        if iid in self._indicators:
            del self._indicators[iid]
        self._invalidate()

    def render(self, size, focus=False):
        self._rebuild()
        return super().render(size, focus)

    def _rebuild(self) -> None:
        left_indicators = self._list_indicators(IndicatorLocation.LEFT)
        right_indicators = self._list_indicators(IndicatorLocation.RIGHT)
        leftmarkup = self._gen_markup(left_indicators)
        rightmarkup = self._gen_markup(right_indicators)
        self.left.set_text(leftmarkup)
        self.right.set_text(rightmarkup)

    def _list_indicators(self, location: IndicatorLocation) -> Sequence[TopIndicator]:
        indicators = self._indicators.values()
        return sorted(
            [i for i in indicators if i.location == location], key=lambda i: i.weight,
        )

    def _gen_markup(self, indicators: Sequence[TopIndicator]) -> UrwidText:
        if not indicators:
            return ""

        out: UrwidText = []
        assert isinstance(out, list)
        for ind in indicators:
            if isinstance(ind.markup, list):
                out.extend(ind.markup)
            else:
                out.append(ind.markup)
            out.append(" ")
            # Remove the last space
        out.pop()
        return out


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

    def draw(self) -> None:
        self._mainloop.draw_screen()

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

    def push_modal(self, activity: Activity, options: api.ModalOptions) -> None:
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

    def push_dialog(self, title: str, content: urwid.Widget) -> api.Dialog:
        dialogact = DialogActivity(self, title, content)
        self.push_modal(dialogact, dialogact.modal_opts)
        return dialogact

    def pop_activity(self) -> None:
        curactctx = self._act_stack.pop()
        for task in curactctx.tasks:
            task.cancel()
        curactctx.activity.hide()
        curactctx.activity.destroy()

        if self._act_stack:
            prevactctx = self._act_stack[-1]
            self._main_view.original_widget = prevactctx.widget
            self._reset_palette(prevactctx.palette)
            prevactctx.activity.show()

    def set_indicator(
        self, iid: str, markup: UrwidText, location: IndicatorLocation, weight: int
    ) -> None:
        self._header.set_indicator(iid, markup, location, weight)

    def remove_indicator(self, iid: str) -> None:
        self._header.remove_indicator(iid)

    def set_status(self, text: api.UrwidText):
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
            (basic, mono, high_88, high_256, high_true) = entry
            signals.emit_signal(
                self._mainloop.screen,
                urwid.UPDATE_PALETTE_ENTRY,
                name,
                basic,
                mono,
                high_88,
                high_256,
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


class DialogActivity(api.Activity, api.Dialog):
    button_widgets: List[urwid.Widget]

    def __init__(
        self, screen: api.ScreenManager, title: str, message: urwid.Widget
    ) -> None:
        self.screen = screen
        self.title = title
        self.message = message
        self.modal_opts = api.ModalOptions(
            align="center",
            width=("relative", 60),
            valign="middle",
            height="pack",
            min_width=54,
        )

        self.custom_buttons = False
        self.button_width = 0

    def create(self) -> urwid.Widget:
        # Add simple default button that can be oberridden by adding custom
        # buttons.
        default_btn_text = "Close"
        btn = widget.PlainButton(default_btn_text)
        self.btn_width = len(default_btn_text) + 2
        urwid.connect_signal(
            btn, "click", self._on_button_clicked, user_args=[lambda: True]
        )
        self.buttons = urwid.GridFlow(
            [btn], cell_width=11, h_sep=2, v_sep=1, align="center",
        )

        content = urwid.Pile([self.message, urwid.Divider(), self.buttons])
        view = urwid.LineBox(content, self.title)
        return view

    def add_button(self, label: str, handler: Callable[[], bool]) -> None:
        if not self.custom_buttons:
            self.buttons.contents = []

        self._update_btn_width(label)
        button = widget.PlainButton(label)
        urwid.connect_signal(
            button, "click", self._on_button_clicked, user_args=[handler]
        )
        contents = [
            (w, ("given", self.button_width)) for w, opts in self.buttons.contents
        ]
        # self.button_widgets.append(button)
        contents.append((button, ("given", self.button_width)))
        self.buttons.contents = contents
        self.custom_buttons = True

    def no_buttons(self) -> None:
        self.buttons.contents = []

    def _on_button_clicked(
        self, handler: Callable[[], bool], btn: urwid.Widget
    ) -> None:
        close_activity = handler()
        if close_activity:
            self.screen.pop_activity()

    def _update_btn_width(self, label: str) -> None:
        new_width = len(label) + 2
        if self.button_width < new_width:
            self.button_width = new_width
