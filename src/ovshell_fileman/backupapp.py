from typing import List, Optional, Coroutine
import asyncio
from dataclasses import dataclass

import urwid
import re

from ovshell import api
from ovshell import widget

from .api import AutomountWatcher
from .usbcurtain import USBStorageCurtain, make_usbstick_watcher
from .utils import format_size


BACKUP_DIRS = [
    "//home/root",
    "//var/lib/connman",
    "//etc/opkg/",
    "//etc/dropbear",
    "//opt/conf",
]

BACKUP_DEST = "openvario/backup"

RSYNC_BIN = "//usr/bin/rsync"
RSYNC_PROGRESS2_RE = r"([\d,]+)\s+(\d+)%\s+([\d\.]+.B\/s)\s+([\d:]+)(\s+\((.*)\))?"


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
        urwid.connect_signal(b_backup, "click", self._on_backup)

        b_restore = widget.PlainButton("Restore")

        b_exit = widget.PlainButton("Exit")
        urwid.connect_signal(b_exit, "click", self._on_exit)

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

    def _on_backup(self, w: urwid.Widget) -> None:
        act = BackupActivity(self.shell)
        opts = api.ModalOptions(
            align="center", width=("relative", 80), valign="middle", height="pack",
        )
        self.shell.screen.push_modal(act, opts)

    def _on_exit(self, w: urwid.Widget) -> None:
        self.shell.screen.pop_activity()


class BackupActivity(api.Activity):
    rsync_task: Optional["asyncio.Task[int]"] = None

    def __init__(self, shell: api.OpenVarioShell) -> None:
        self.shell = shell

    def create(self) -> None:
        self._progress = RsyncProgressBar(self.shell.os, [])
        urwid.connect_signal(self._progress, "done", self._on_sync_done)
        urwid.connect_signal(self._progress, "failed", self._on_sync_failed)

        self._b_close = widget.PlainButton("Close")
        urwid.connect_signal(self._b_close, "click", self._on_close)

        b_cancel = widget.PlainButton("Cancel")
        urwid.connect_signal(b_cancel, "click", self._on_cancel)

        self.status_msg = urwid.Text("\n")

        self._button_row = urwid.GridFlow([b_cancel], 16, 1, 1, align="center")

        content = urwid.Pile(
            [urwid.Divider(), self._progress, self.status_msg, self._button_row,]
        )
        w = urwid.LineBox(content, title="Backup")
        return w

    def activate(self) -> None:
        self.rsync_task = self.shell.screen.spawn_task(self, self._progress.start())

    def _on_cancel(self, w: urwid.Widget) -> None:
        self.shell.screen.pop_activity()

        if self.rsync_task is None:
            return

        if not self.rsync_task.done():
            self.rsync_task.cancel()
            self.shell.screen.push_dialog(
                "Backup cancelled", urwid.Text("Backup was not completed.")
            )

    def _on_close(self, w: urwid.Widget) -> None:
        self.shell.screen.pop_activity()

    def _on_sync_done(self, w: urwid.Widget) -> None:
        self.status_msg.set_text(
            ["\n", ("success message", "Backup has completed."), "\n"]
        )
        self._button_row.contents = [(self._b_close, ("given", 16))]

    def _on_sync_failed(self, w: urwid.Widget, res: int) -> None:
        self.status_msg.set_text(
            ["\n", ("error message", f"Backup has failed (error code: {res})."), "\n"]
        )
        self._button_row.contents = [(self._b_close, ("given", 16))]


@dataclass
class RsyncStatusLine:
    transferred: int  # bytes
    progress: int  # %
    rate: str
    elapsed: str
    xfr: Optional[str]

    @staticmethod
    def parse(line: bytes) -> Optional["RsyncStatusLine"]:
        match = re.match(RSYNC_PROGRESS2_RE, line.strip().decode())
        if match is None:
            return None

        return RsyncStatusLine(
            transferred=int(match.group(1).replace(",", "")),
            progress=int(match.group(2)),
            rate=match.group(3),
            elapsed=match.group(4),
            xfr=match.group(6),
        )


class RsyncProgressBar(urwid.ProgressBar):
    signals = ["done", "failed"]

    def __init__(self, os: api.OpenVarioOS, rsync_params: List[str]) -> None:
        self.os = os
        self.rsync_params = rsync_params
        self._current_progress = ""
        super().__init__("pg inverted", "pg complete")

    async def start(self) -> None:
        proc = await asyncio.create_subprocess_exec(
            self.os.path(RSYNC_BIN),
            *self.rsync_params,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            limit=100,
        )

        assert proc.stdout is not None

        while not proc.stdout.at_eof():
            try:
                line = await proc.stdout.readuntil(b"\r")
            except asyncio.IncompleteReadError:
                break
            rsync_progress = RsyncStatusLine.parse(line)
            if rsync_progress is not None:
                self._set_progress(rsync_progress)

        result = await proc.wait()
        if result == 0:
            self._emit("done")
        else:
            self._emit("failed", result)

    def get_text(self) -> str:
        return self._current_progress

    def _set_progress(self, prg: RsyncStatusLine) -> None:
        self.set_completion(prg.progress)
        transferred = format_size(prg.transferred)
        self._current_progress = (
            f"{prg.progress}% | {transferred} | {prg.rate} | {prg.elapsed}"
        )
