from typing import Sequence
import subprocess

from ovshell import protocol

import urwid


class AppOutputActivity(protocol.Activity):
    def __init__(self, shell: protocol.OpenVarioShell, message: str) -> None:
        self.shell = shell
        self.message = message

    def create(self) -> urwid.Widget:
        term = urwid.Text(self.message)
        view = urwid.LineBox(term, "Error")
        return view


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
        modal_opts = protocol.ModalOptions(
            align="center", width=("relative", 90), valign="middle", height="pack",
        )
        try:
            completed = subprocess.run([binary, "-fly"], capture_output=True)
        except FileNotFoundError as e:
            self.shell.screen.push_modal(
                AppOutputActivity(self.shell, str(e)), modal_opts
            )
            return

        if completed.returncode != 0:
            self.shell.screen.push_modal(
                AppOutputActivity(self.shell, completed.stderr.decode("utf-8")),
                modal_opts,
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
