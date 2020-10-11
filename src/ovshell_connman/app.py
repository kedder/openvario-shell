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
    def __init__(self, shell: api.OpenVarioShell, manager: ConnmanManager) -> None:
        self.shell = shell
        self.manager = manager

    def create(self) -> urwid.Widget:
        # view = urwid.SolidFill("*")

        self._svc_walker = urwid.SimpleFocusListWalker([urwid.Text("ONE")])
        self._tech_grid = urwid.GridFlow([], 25, 1, 1, "left")

        view = urwid.Pile(
            [
                ("pack", urwid.Text("Technologies")),
                ("pack", self._tech_grid),
                ("pack", urwid.Text("Connections")),
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
        cols = urwid.Columns(
            [
                ("fixed", 2, urwid.Text("*" if svc.favorite else " ")),
                ("weight", 2, urwid.Text(svc.name)),
                ("weight", 1, urwid.Text(str(svc.strength))),
                # ("weight", 1, urwid.Text(svc.type)),
            ]
        )
        return widget.SelectableItem(cols)
