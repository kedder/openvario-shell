import urwid

from ovshell import api
from ovshell import widget

from .api import AutomountWatcher
from .usbcurtain import USBStorageCurtain, make_usbstick_watcher


BACKUP_DIRS = [
    "//home/root",
    "//var/lib/connman",
    "//etc/opkg/",
    "//etc/dropbear",
    "//opt/conf",
]

BACKUP_DEST = "openvario/backup"


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
        disclaimer = urwid.Text(
            [
                "The following directories will be backed up to USB stick directory ",
                ("highlight", BACKUP_DEST),
                ":",
            ]
        )

        absdirs = [self.shell.os.path(d) for d in BACKUP_DIRS]
        backupdirs = urwid.Pile([urwid.Text(f"  * {d}") for d in absdirs])

        b_backup = widget.PlainButton("Backup")
        b_restore = widget.PlainButton("Restore")
        b_exit = widget.PlainButton("Exit")
        buttons = urwid.GridFlow(
            [b_backup, b_restore, b_exit],
            cell_width=15,
            h_sep=1,
            v_sep=1,
            align="left",
        )

        self._app_view = urwid.Filler(
            urwid.Pile(
                [disclaimer, urwid.Divider(), backupdirs, urwid.Divider(), buttons]
            ),
            "top",
        )

        # _stub = urwid.Text("Backup & Restore", align="center")
        # self._app_view = urwid.Filler(_stub, "middle")

        curtain = USBStorageCurtain(self.mountwatcher, self._app_view)

        self.frame = urwid.Frame(
            curtain, header=widget.ActivityHeader("Backup & Restore")
        )
        return self.frame

    def activate(self) -> None:
        self.shell.screen.spawn_task(self, self.mountwatcher.run())
