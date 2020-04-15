from typing import Sequence, Dict
import subprocess
import os

from ovshell import protocol

import urwid


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


class XCSoarApp(protocol.App):
    name = "xcsoar"
    title = "XCSoar"
    description = "Tactical glide computer"
    priority = 90

    def __init__(self, shell: protocol.OpenVarioShell) -> None:
        self.shell = shell

    def install(self, appinfo: protocol.AppInfo) -> None:
        self.shell.apps.pin(appinfo)

    def launch(self) -> None:
        self._set_orientation_in_profile()
        env = self._prep_environment()
        cmdline = self._make_commandline()
        modal_opts = protocol.ModalOptions(
            align="center", width=("relative", 90), valign="middle", height="pack",
        )
        try:
            completed = subprocess.run(cmdline, capture_output=True, env=env)
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

    def _set_orientation_in_profile(self) -> None:
        # Map from ovshell orientation to xcsoar orientation
        orient_map = {
            "0": "0",  # normal
            "1": "1",  # portrait (90)
            "2": "4",  # landscape (180)
            "3": "3",  # portrait (270)
        }

        orientation = self.shell.settings.getstrict("core.screen_orientation", str)
        xcsoar_orient = orient_map[orientation]

        prf_fname = self._find_xcsoar_profile()
        prf = XCSoarProfile(self.shell.os, prf_fname)
        prf.set_orientation(xcsoar_orient)
        prf.save()

    def _prep_environment(self) -> Dict[str, str]:
        env = os.environ.copy()
        lang = self.shell.settings.get("core.language", str)
        if lang is None:
            return env

        env["LANG"] = lang
        return env

    def _make_commandline(self) -> Sequence[str]:
        os = self.shell.os
        binary = os.host_path(self.shell.settings.getstrict("xcsoar.binary", str))
        return [binary, "-fly"]

    def _find_xcsoar_profile(self) -> str:
        xcs_home = self.shell.settings.getstrict("xcsoar.home", str)

        profiles = ["openvario.prf", "default.prf"]
        for fname in profiles:
            prf_fname = os.path.join(xcs_home, fname)
            if self.shell.os.file_exists(prf_fname):
                return prf_fname

        raise RuntimeError(f"Cannot find XCSoar profile in {xcs_home}")


class AppOutputActivity(protocol.Activity):
    def __init__(self, shell: protocol.OpenVarioShell, message: str) -> None:
        self.shell = shell
        self.message = message

    def create(self) -> urwid.Widget:
        term = urwid.Text(self.message)
        view = urwid.LineBox(term, "Error")
        return view


class XCSoarProfile:
    def __init__(self, os: protocol.OpenVarioOS, filename: str) -> None:
        self.os = os
        self.filename = filename

        profile = os.read_file(filename)
        self.lines = profile.split(b"\n")

    def save(self) -> None:
        content = b"\n".join(self.lines)
        self.os.write_file(self.filename, content)

    def set_orientation(self, orientation: str) -> None:
        self._set_option("DisplayOrientation", orientation)

    def _set_option(self, key: str, value: str) -> None:
        modified_line = f'{key}="{value}"'.encode()
        bkey = key.encode()
        for n, line in enumerate(self.lines):
            k, v = line.split(b"=", maxsplit=1)
            if k == bkey:
                self.lines[n] = modified_line
                break
        else:
            self.lines.append(modified_line)
