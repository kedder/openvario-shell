import os
import subprocess
from typing import Sequence

import urwid

from ovshell import api


class XCSoarExtension(api.Extension):
    title = "XCSoar"

    def __init__(self, id: str, shell: api.OpenVarioShell):
        self.id = id
        self.shell = shell

    def list_apps(self) -> Sequence[api.App]:
        return [XCSoarApp(self.shell)]


class XCSoarApp(api.App):
    name = "xcsoar"
    title = "XCSoar"
    description = "Tactical glide computer"
    priority = 90

    def __init__(self, shell: api.OpenVarioShell) -> None:
        self.shell = shell

    def install(self, appinfo: api.AppInfo) -> None:
        self.shell.apps.pin(appinfo)

    def launch(self) -> None:
        env = self._prep_environment()
        cmdline = self._make_commandline()
        modal_opts = api.ModalOptions(
            align="center",
            width=("relative", 90),
            valign="middle",
            height="pack",
        )
        try:
            message = urwid.Text("Running XCSoar...")
            self.shell.screen.push_dialog("XCSoar", message).no_buttons()
            self.shell.screen.draw()
            try:
                completed = subprocess.run(cmdline, capture_output=True, env=env)
            finally:
                message.set_text("Finishing XCSoar...")
                self.shell.screen.draw()
                self.shell.os.sync()
                self.shell.screen.pop_activity()
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

    def _prep_environment(self) -> dict[str, str]:
        env = os.environ.copy()
        lang = self.shell.settings.get("core.language", str)
        if lang is None:
            return env

        env["LANG"] = lang
        return env

    def _make_commandline(self) -> Sequence[str]:
        binary = os.environ.get("XCSOAR_BIN", "/usr/bin/xcsoar")
        return [binary, "-fly"]


class AppOutputActivity(api.Activity):
    def __init__(self, shell: api.OpenVarioShell, message: str) -> None:
        self.shell = shell
        self.message = message

    def create(self) -> urwid.Widget:
        term = urwid.Text(self.message)
        view = urwid.LineBox(term, "Error")
        return view


class XCSoarProfile:
    def __init__(self, filename: str) -> None:
        self.os = os
        self.filename = filename
        self._dirty = False

        with open(filename) as f:
            self.lines = f.readlines()

    def save(self) -> None:
        if not self._dirty:
            return
        content = "".join(self.lines)
        with open(self.filename, "w") as f:
            f.write(content)

    def set_orientation(self, orientation: str) -> None:
        self._set_option("DisplayOrientation", orientation)

    def _set_option(self, key: str, value: str) -> None:
        modified_line = f'{key}="{value}"\n'
        for n, line in enumerate(self.lines):
            if "=" not in line:
                continue
            k, v = line.split("=", maxsplit=1)
            v = v.strip('\n"')
            if k == key:
                self.lines[n] = modified_line
                self._dirty = v != value
                break
        else:
            self.lines.append(modified_line)
            self._dirty = True
