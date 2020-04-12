from typing import Sequence, List, Optional

import urwid

from ovshell import protocol


class AppRowItem(urwid.WidgetWrap):
    def __init__(self, app: protocol.App) -> None:
        self._app = app
        self._title_w = urwid.Text(app.title)
        self._descr_w = urwid.Text(app.description)
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
        btxt = urwid.BigText("Apps", urwid.font.Thin6x6Font())
        logo = urwid.Padding(btxt, "left", "clip")

        menuitems = []
        for app in self._get_apps():
            menuitems.append(AppRowItem(app))

        menu = urwid.Pile(menuitems)

        view = urwid.Filler(
            urwid.Pile([logo, urwid.Padding(menu, align=urwid.CENTER)]), "top"
        )
        return view

    def _get_apps(self) -> Sequence[protocol.App]:
        settings: List[protocol.App] = []
        for ext in self.shell.extensions.list_extensions():
            settings.extend(ext.list_apps())

        return sorted(settings, key=lambda s: -s.priority)
