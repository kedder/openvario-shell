from typing import Optional

import urwid

from ovshell import protocol
from ovshell import widget


class AppRowItem(urwid.WidgetWrap):
    def __init__(self, appinfo: protocol.AppInfo) -> None:
        self._app = appinfo.app
        self._title_w = urwid.Text(appinfo.app.title)
        self._descr_w = urwid.Text(appinfo.app.description)
        cols = urwid.Columns(
            [("weight", 1, self._title_w), ("weight", 3, self._descr_w)]
        )
        wdg = urwid.AttrMap(cols, "li normal", "li focus")
        super().__init__(wdg)

    def selectable(self):
        return True

    def keypress(self, size, key: str) -> Optional[str]:
        if self._command_map[key] == "activate":
            self._app.launch()
            return None
        return key


class AppsActivity(protocol.Activity):
    def __init__(self, shell: protocol.OpenVarioShell) -> None:
        self.shell = shell

    def create(self) -> urwid.Widget:
        header = widget.ActivityHeader("Applications")

        menuitems = []
        for appinfo in self.shell.apps.list():
            menuitems.append(AppRowItem(appinfo))

        menu = urwid.Pile(menuitems)

        view = urwid.Filler(
            urwid.Pile([header, urwid.Padding(menu, align=urwid.CENTER)]), "top"
        )
        return view
