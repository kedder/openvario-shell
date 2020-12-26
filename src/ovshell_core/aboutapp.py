from typing import Coroutine, List, Optional

import urwid

from ovshell import api, widget
from ovshell_core.opkg import create_opkg_tools
from ovshell_core.sysinfo import SystemInfo, SystemInfoImpl

OV_HOMEPAGE = "https://openvario.org/"
OVSHELL_HOMEPAGE = "https://github.com/kedder/openvario-shell"


class AboutApp(api.App):
    name = "about"
    title = "About"
    description = "Show information about this device"
    priority = 1

    def __init__(self, shell: api.OpenVarioShell) -> None:
        self.shell = shell

    def launch(self) -> None:
        act = AboutActivity(self.shell)
        self.shell.screen.push_activity(act)


class AboutActivity(api.Activity):
    sys_info: SystemInfo

    def __init__(self, shell: api.OpenVarioShell) -> None:
        self.shell = shell
        self.sys_info = SystemInfoImpl(shell.os, create_opkg_tools(shell.os))

    def create(self) -> urwid.Widget:
        header = widget.ActivityHeader("About Openvario")

        about_ov = urwid.Text(
            [
                ("highlight", "About Openvario"),
                "\n\n",
                (
                    "Openvario is a project that aims to create a high performance, "
                    "open source flight computer."
                ),
                "\n\n",
                f"See {OV_HOMEPAGE} for more info.",
            ]
        )

        about_ovshell = urwid.Text(
            [
                ("highlight", "About Openvario Shell"),
                "\n\n",
                (
                    "Openvario Shell (this app) is a user interface application "
                    "to control, manage and configure your Openvario device."
                ),
                "\n\n",
                f"See {OVSHELL_HOMEPAGE} for more info.",
            ]
        )

        versions_header = urwid.Text([("highlight", "System information")])

        self.versions = urwid.Pile([])

        view = urwid.Filler(
            urwid.Pile(
                [
                    header,
                    about_ov,
                    urwid.Divider(),
                    about_ovshell,
                    urwid.Divider(),
                    versions_header,
                    urwid.Divider(),
                    self.versions,
                ]
            ),
            "top",
        )
        return view

    def activate(self) -> None:
        self._populate_versions()

    def _populate_versions(self) -> None:
        ver_defs = [
            ("Openvario image", self.sys_info.get_openvario_version()),
            ("XCSoar", self._get_any_version(["xcsoar", "xcsoar-testing"])),
            ("Sensor daemon", self._get_any_version(["sensord", "sensord-testing"]),),
            ("Vario daemon", self._get_any_version(["variod", "variod-testing"]),),
            ("Linux kernel", self.sys_info.get_kernel_version()),
            ("Hostname", self.sys_info.get_hostname()),
        ]
        contents = [(self._make_version_wdg(t, f), ("pack", None)) for t, f in ver_defs]
        self.versions.contents = contents

    def _make_version_wdg(
        self, title: str, fetcher: Coroutine[None, None, Optional[str]]
    ) -> urwid.Widget:
        version_wdg = urwid.Text(("progress", "..."))
        self.shell.screen.spawn_task(self, self._update_version(version_wdg, fetcher))
        return urwid.Columns(
            [("weight", 1, urwid.Text(title)), ("weight", 3, version_wdg)],
            dividechars=1,
        )

    async def _update_version(
        self, wdg: urwid.Text, fetcher: Coroutine[None, None, Optional[str]]
    ) -> None:
        ver = await fetcher
        if ver is not None:
            wdg.set_text(("success message", ver))
        else:
            wdg.set_text("N/A")

    async def _get_any_version(self, pkgs: List[str]) -> Optional[str]:
        for pkgname in pkgs:
            ver = await self.sys_info.get_installed_package_version(pkgname)
            if ver is not None:
                return ver
        return None
