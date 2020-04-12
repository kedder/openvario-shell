from typing import Sequence
import subprocess

from ovshell import protocol

import urwid


class AppOutputActivity(protocol.Activity):
    def __init__(self, shell: protocol.OpenVarioShell, message: str) -> None:
        self.shell = shell
        self.message = message

    def create(self) -> urwid.Widget:
        # btxt = urwid.BigText("XCSoar", urwid.font.Thin6x6Font())
        # logo = urwid.Padding(btxt, "center", "clip")

        term = urwid.Text(self.message)
        view = urwid.LineBox(urwid.Filler(term, "top"), "Error")

        bg = self.shell.screen._main_view.original_widget
        ovl = urwid.Overlay(
            view,
            bg,
            align="center",
            width=("relative", 90),
            valign="middle",
            height=("relative", 90),
        )
        return ovl


class XCSoarApp(protocol.App):
    name = "xcsoar"
    title = "XCSoar"
    description = "Tactical glide computer"
    priority = 90

    def __init__(self, shell: protocol.OpenVarioShell) -> None:
        self.shell = shell

    def launch(self) -> None:
        # self.shell.screen.push_activity(AppOutputActivity(self.shell))
        binary = self.shell.settings.get("xcsoar.binary", str)
        assert binary is not None
        try:
            completed = subprocess.run([binary, "-fly"], capture_output=True)
        except FileNotFoundError as e:
            self.shell.screen.push_activity(AppOutputActivity(self.shell, str(e)))
            return

        if completed.returncode != 0:
            self.shell.screen.push_activity(
                AppOutputActivity(self.shell, completed.stderr.decode("utf-8"))
            )


class XCSoarExtension(protocol.Extension):
    title = "XCSoar"

    def __init__(self, id: str, shell: protocol.OpenVarioShell):
        self.id = id
        self.shell = shell
        self._init_settings()

    def list_apps(self) -> Sequence[protocol.App]:
        return [XCSoarApp(self.shell)]

    def _init_settings(self) -> None:
        config = self.shell.settings
        config.setdefault("xcsoar.binary", "/opt/XCSoar/bin/xcsoar")
        config.setdefault("xcsoar.home", "/home/root/.xcsoar")
