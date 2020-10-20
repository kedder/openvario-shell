from typing import Optional, Dict
import os
import asyncio

import urwid

from ovshell import api
from ovshell import widget
from ovshell_connman.api import ConnmanManager, ConnmanService
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
    _conn_waits: Dict[str, widget.Waiting]

    def __init__(self, shell: api.OpenVarioShell, manager: ConnmanManager) -> None:
        self.shell = shell
        self.manager = manager
        self._conn_waits = {}

    def create(self) -> urwid.Widget:
        # view = urwid.SolidFill("*")

        self._svc_walker = urwid.SimpleFocusListWalker([urwid.Text("ONE")])
        self._tech_grid = urwid.GridFlow([], 25, 1, 1, "left")

        view = urwid.Pile(
            [
                ("pack", urwid.Text("Technologies")),
                ("pack", self._tech_grid),
                ("pack", urwid.Text("Connections")),
                ("pack", self._make_scan_button()),
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

    def _make_scan_button(self) -> urwid.Widget:
        btn = widget.PlainButton("Scan")
        urwid.connect_signal(btn, "click", self._handle_scan)
        self.scan_waiting = widget.Waiting(6)
        return urwid.Columns([(8, btn), ("pack", self.scan_waiting)], dividechars=1)

    def _handle_scan(self, w: urwid.Widget) -> None:
        task = self.shell.screen.spawn_task(self, self.manager.scan_all())
        self.scan_waiting.start_waiting_for(task)

    def _handle_techs_changed(self) -> None:
        contents = []
        for tech in self.manager.technologies:
            cb = urwid.CheckBox(tech.name, state=tech.powered)
            contents.append((cb, (urwid.GIVEN, 25)))

        self._tech_grid.contents = contents

    def _handle_svcs_changed(self) -> None:
        contents = []
        for svc in self.manager.services:
            contents.append(self._make_service_row(svc))

        del self._svc_walker[:]
        self._svc_walker.extend(contents)
        self._svc_walker.set_focus(0)

    def _make_service_row(self, svc: ConnmanService) -> urwid.Widget:
        waiting = self._conn_waits.setdefault(svc.path, widget.Waiting(4))

        cols = urwid.Columns(
            [
                ("fixed", 2, urwid.Text("*" if svc.favorite else " ")),
                ("weight", 3, urwid.Text(svc.name)),
                ("fixed", 4, waiting),
                ("weight", 1, urwid.Text(str(svc.strength))),
                # ("weight", 1, urwid.Text(str(svc.state))),
                # ("weight", 1, urwid.Text(svc.type)),
            ]
        )
        item = widget.SelectableItem(cols)
        urwid.connect_signal(
            item, "click", self._handle_service_clicked, user_args=[svc]
        )
        return item

    def _handle_service_clicked(self, svc: ConnmanService, w: urwid.Widget) -> None:
        self.shell.screen.spawn_task(self, self._connect(svc))

    async def _connect(self, svc: ConnmanService) -> None:
        waiting = self._conn_waits[svc.path]
        await waiting.wait_for(self.manager.connect(svc))
        # dlg = self.shell.screen.push_dialog(svc.name, urwid.Text("Connecting..."))
        # dlg.no_buttons()
        # try:
        #     await self.manager.connect(svc)
        # finally:
        #     self.shell.screen.pop_activity()
