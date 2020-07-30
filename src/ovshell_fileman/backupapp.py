import urwid

from ovshell import api
from ovshell import widget

from .api import AutomountWatcher
from .usbcurtain import USBStorageCurtain, make_usbstick_watcher


class BackupRestoreApp(api.App):
    name = "backup"
    title = "Backup"
    description = "Backup & restore configuration and data"
    priority = 40

    def __init__(self, shell: api.OpenVarioShell):
        self.shell = shell

    def launch(self) -> None:
        act = BackupRestoreMainActivity(
            self.shell, make_usbstick_watcher(self.shell.os)
        )
        self.shell.screen.push_activity(act)


class BackupRestoreMainActivity(api.Activity):
    def __init__(
        self, shell: api.OpenVarioShell, mountwatcher: AutomountWatcher,
    ) -> None:
        self.shell = shell
        self.mountwatcher = mountwatcher

    def create(self) -> urwid.Widget:
        _stub = urwid.Text("Backup & Restore", align="center")
        self._app_view = urwid.Filler(_stub, "middle")

        curtain = USBStorageCurtain(self.mountwatcher, self._app_view)

        self.frame = urwid.Frame(
            curtain, header=widget.ActivityHeader("Backup & Restore")
        )
        return self.frame

    def activate(self) -> None:
        self.shell.screen.spawn_task(self, self.mountwatcher.run())
