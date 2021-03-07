import asyncio
from typing import Callable, Coroutine, Dict, Optional

import urwid

from ovshell import api, widget
from ovshell_connman.api import ConnmanManager, ConnmanService, ConnmanServiceState
from ovshell_connman.api import ConnmanTechnology
from ovshell_connman.manager import ConnmanManagerImpl


class ConnmanManagerApp(api.App):
    name = "connman-manager"
    title = "Networking"
    description = "Set up WiFi and other network connections"
    priority = 30

    def __init__(self, shell: api.OpenVarioShell):
        self.shell = shell

    def launch(self) -> None:
        dialog = self.shell.screen.push_dialog(
            "Connecting", urwid.Text("Connecting to D-BUS...")
        )
        dialog.no_buttons()
        self.shell.screen.draw()
        asyncio.create_task(self.launch_async())

    async def launch_async(self) -> None:
        try:
            bus = await self.shell.os.get_system_bus()
        except api.DBusNotAvailableException:
            self.shell.screen.pop_activity()
            self.shell.screen.push_dialog(
                "Unable to connect", urwid.Text("D-BUS is not available")
            )
            return

        self.shell.screen.pop_activity()
        manager = ConnmanManagerImpl(bus)
        act = ConnmanManagerActivity(self.shell, manager)
        self.shell.screen.push_activity(act)


class ConnmanManagerActivity(api.Activity):
    _svc_waits: Dict[str, widget.Waiting]

    _techs_grid: Optional[urwid.GridFlow] = None

    def __init__(self, shell: api.OpenVarioShell, manager: ConnmanManager) -> None:
        self.shell = shell
        self.manager = manager
        self._svc_waits = {}

    def create(self) -> urwid.Widget:
        # view = urwid.SolidFill("*")

        self._svc_walker = urwid.SimpleFocusListWalker([urwid.Text("")])
        self._techs_ph = urwid.WidgetPlaceholder(urwid.Text(""))

        view = urwid.Pile(
            [
                ("pack", self._techs_ph),
                ("pack", urwid.Divider()),
                ("pack", self._make_service_header()),
                urwid.ListBox(self._svc_walker),
            ]
        )

        self.frame = urwid.Frame(
            view, header=widget.ActivityHeader("Network connections")
        )
        return self.frame

    def activate(self) -> None:
        self.manager.on_technologies_changed(self._handle_techs_changed)
        self.manager.on_services_changed(self._handle_svcs_changed)
        self.shell.screen.spawn_task(self, self.manager.setup())

    def destroy(self) -> None:
        self.manager.teardown()

    def _make_scan_button(self) -> urwid.Widget:
        btn = widget.PlainButton("Scan")
        urwid.connect_signal(btn, "click", self._handle_scan)
        self.scan_waiting = widget.Waiting(6)
        return urwid.Columns([(8, btn), ("pack", self.scan_waiting)], dividechars=1)

    def _handle_scan(self, w: urwid.Widget) -> None:
        task = self.shell.screen.spawn_task(self, self.manager.scan_all())
        self.scan_waiting.start_waiting_for(task)

    def _handle_techs_changed(self) -> None:
        # Remember the old focus
        focus = 0
        if self._techs_grid is not None:
            focus = self._techs_grid.focus_position

        contents = []
        for tech in self.manager.technologies:

            lbl = ("enabled" if tech.powered else "disabled", tech.name)
            cb = urwid.CheckBox(lbl, state=tech.powered)
            urwid.connect_signal(
                cb, "change", self._handle_tech_power, user_args=[tech]
            )
            contents.append(cb)

        self._techs_grid = urwid.GridFlow(contents, 25, 1, 1, "left")
        self._techs_grid.set_focus(focus)
        self._techs_ph.original_widget = urwid.LineBox(
            urwid.Pile([self._techs_grid, urwid.Divider(), self._make_scan_button()]),
            title="Technologies",
            title_align="left",
        )

    def _handle_tech_power(
        self, tech: ConnmanTechnology, cb: urwid.CheckBox, state: bool
    ) -> None:
        self.shell.screen.spawn_task(self, self.manager.power(tech, state))

    def _handle_svcs_changed(self) -> None:
        _, focus_pos = self._svc_walker.get_focus()
        contents = []
        for svc in self.manager.list_services():
            contents.append(self._make_service_row(svc))

        del self._svc_walker[:]
        self._svc_walker.extend(contents)

        # restore focus
        if focus_pos is None:
            focus_pos = 0
        if focus_pos >= len(self._svc_walker):
            focus_pos = len(contents) - 1
        if focus_pos >= 0:
            self._svc_walker.set_focus(focus_pos or 0)

    def _make_service_header(self) -> urwid.Widget:
        cols = urwid.Columns(
            [
                ("fixed", 6, urwid.Text("Signal")),
                ("fixed", 1, urwid.Text("")),
                ("weight", 3, urwid.Text("Service")),
                ("fixed", 4, urwid.Text("")),
                ("weight", 1, urwid.Text("State")),
            ],
            dividechars=1,
        )
        return cols

    def _make_service_row(self, svc: ConnmanService) -> urwid.Widget:
        waiting = self._svc_waits.setdefault(svc.path, widget.Waiting(4))
        strength_wdg = StrengthBar(svc.strength, align=urwid.RIGHT)

        cols = urwid.Columns(
            [
                ("fixed", 6, strength_wdg),
                ("fixed", 1, urwid.Text("*" if svc.favorite else " ")),
                ("weight", 3, urwid.Text(svc.name)),
                ("fixed", 4, waiting),
                ("weight", 1, urwid.Text(svc.state.value)),
            ],
            dividechars=1,
        )
        item = widget.SelectableItem(cols)
        urwid.connect_signal(
            item, "click", self._handle_service_clicked, user_args=[svc]
        )
        return urwid.AttrMap(
            item,
            {},
            {
                "progress": "li focus",
                "str good": "li focus",
                "str weak": "li focus",
                "str average": "li focus",
            },
        )

    def _handle_service_clicked(self, svc: ConnmanService, w: urwid.Widget) -> None:
        # Find what actions we can perform with this service
        actions = []
        can_connect = False
        if svc.state in (ConnmanServiceState.IDLE, ConnmanServiceState.FAILURE):
            can_connect = True
            actions.append(("Connect", self._connect))

        if svc.favorite:
            actions.append(("Forget", self._forget))

        if svc.state in (ConnmanServiceState.ONLINE, ConnmanServiceState.READY):
            actions.append(("Disconnect", self._disconnect))

        if can_connect and len(actions) == 1:
            # The only action we can do here is to connect, just do that
            # immediately.
            self.shell.screen.spawn_task(self, self._connect(svc))
            return

        dialog = self.shell.screen.push_dialog(
            svc.name, urwid.Text("Available actions:")
        )
        for label, action in actions:

            def handler(
                a: Callable[[ConnmanService], Coroutine] = action,
                s: ConnmanService = svc,
            ) -> bool:
                self.shell.screen.spawn_task(self, a(s))
                return True

            dialog.add_button(label, handler)

    async def _connect(self, svc: ConnmanService) -> None:
        waiting = self._svc_waits[svc.path]
        await waiting.wait_for(self.manager.connect(svc))

    async def _forget(self, svc: ConnmanService) -> None:
        waiting = self._svc_waits[svc.path]
        await waiting.wait_for(self.manager.remove(svc))

    async def _disconnect(self, svc: ConnmanService) -> None:
        waiting = self._svc_waits[svc.path]
        await waiting.wait_for(self.manager.disconnect(svc))


class StrengthBar(urwid.Widget):
    _sizing = frozenset([urwid.FLOW])
    _block = "\N{BLACK SQUARE}"  # ■

    def __init__(self, strength: int, align: str = urwid.LEFT) -> None:
        self._strength = strength
        self._align = align

    def rows(self, size, focus=False):
        return 1

    def render(self, size, focus=False) -> urwid.Canvas:
        (maxcol,) = size

        color = "str weak"
        if self._strength > 33:
            color = "str average"
        if self._strength > 66:
            color = "str good"

        filled = int(round(self._strength / 100.0 * maxcol))
        bar = self._block * filled
        txt = urwid.Text((color, bar), align=self._align)
        c = txt.render((maxcol,))
        return c
