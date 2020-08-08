from typing import List, Optional, Coroutine
import os
import re
import asyncio
from abc import abstractmethod
from pathlib import Path
from dataclasses import dataclass

import urwid

from ovshell import api
from ovshell import widget

from .api import AutomountWatcher
from .usbcurtain import USBStorageCurtain, make_usbstick_watcher, USB_MOUNTPOINT
from .utils import format_size


BACKUP_DIRS = [
    "/home/root",
    "/var/lib/connman",
    "/etc/opkg",
    "/etc/dropbear",
    "/opt/conf",
]

EXCLUDES = [
    "/home/root/.profile",
    "/home/root/.cache",
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

        backupdirs = urwid.Pile([urwid.Text(f"  * {d}") for d in BACKUP_DIRS])

        b_backup = widget.PlainButton("Backup")
        urwid.connect_signal(b_backup, "click", self._on_backup)

        b_restore = widget.PlainButton("Restore")
        urwid.connect_signal(b_restore, "click", self._on_restore)

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
        self.shell.screen.push_modal(act, self._get_rsync_modal_opts())

    def _on_restore(self, w: urwid.Widget) -> None:
        act = RestoreActivity(self.shell)
        self.shell.screen.push_modal(act, self._get_rsync_modal_opts())

    def _get_rsync_modal_opts(self) -> api.ModalOptions:
        return api.ModalOptions(
            align="center", width=("relative", 80), valign="middle", height="pack",
        )

    def _on_exit(self, w: urwid.Widget) -> None:
        self.shell.screen.pop_activity()


class RsyncProgressActivity(api.Activity):
    rsync_task: Optional["asyncio.Task[int]"] = None

    msg_title: str
    msg_description: str
    msg_sync_completed: str
    msg_sync_cancelled: str
    msg_sync_failed: str

    def __init__(self, shell: api.OpenVarioShell) -> None:
        self.shell = shell

    @abstractmethod
    def get_rsync_params(self) -> List[str]:
        pass

    def create(self) -> None:
        self._progress = RsyncProgressBar(self.shell.os, self.get_rsync_params())
        urwid.connect_signal(self._progress, "done", self._on_sync_done)
        urwid.connect_signal(self._progress, "failed", self._on_sync_failed)

        self._b_close = widget.PlainButton("Close")
        urwid.connect_signal(self._b_close, "click", self._on_close)

        b_cancel = widget.PlainButton("Cancel")
        urwid.connect_signal(b_cancel, "click", self._on_cancel)

        self.status_msg = urwid.Text("\n")

        self._button_row = urwid.GridFlow([b_cancel], 16, 1, 1, align="center")

        content = urwid.Pile(
            [
                urwid.Divider(),
                urwid.Text(self.msg_description),
                urwid.Divider(),
                self._progress,
                self.status_msg,
                self._button_row,
            ]
        )
        w = urwid.LineBox(content, title=self.msg_title)
        return w

    def activate(self) -> None:
        self.rsync_task = self.shell.screen.spawn_task(self, self._progress.start())

    def _on_cancel(self, w: urwid.Widget) -> None:
        if self.rsync_task is None:
            return

        if not self.rsync_task.done():
            self.rsync_task.cancel()
            self.status_msg.set_text(
                ["\n", ("error message", self.msg_sync_cancelled), "\n"]
            )
            self._show_close_button()

    def _on_close(self, w: urwid.Widget) -> None:
        self.shell.screen.pop_activity()

    def _on_sync_done(self, w: urwid.Widget) -> None:
        self.status_msg.set_text(
            ["\n", ("success message", self.msg_sync_completed), "\n"]
        )
        self._show_close_button()

    def _on_sync_failed(self, w: urwid.Widget, res: int, errors: str) -> None:
        self.status_msg.set_text(
            [
                "\n",
                ("error message", self.msg_sync_failed.format(res=res)),
                "\n\n",
                ("error message", errors),
            ]
        )
        self._show_close_button()

    def _show_close_button(self) -> None:
        self._button_row.contents = [(self._b_close, ("given", 16))]


class BackupActivity(RsyncProgressActivity):
    msg_title = "Backup"
    msg_description = "Copying files from Openvario to USB stick..."
    msg_sync_completed = "Backup has completed."
    msg_sync_cancelled = "Backup was cancelled."
    msg_sync_failed = "Backup has failed (error code: {res})."

    def get_rsync_params(self) -> List[str]:
        mntpoint = self.shell.os.path(USB_MOUNTPOINT)
        assert os.path.exists(mntpoint)
        src_dir = self.shell.os.path("//")
        dest_dir = os.path.join(mntpoint, "openvario", "backup")
        os.makedirs(dest_dir, exist_ok=True)

        excludes = [f"--exclude={exc}" for exc in EXCLUDES]

        allparents = set()
        includes = []
        for bdir in BACKUP_DIRS:
            allparents.update(self._get_all_parents(bdir))
            includes.append(f"--include={bdir}/**")

        parent_includes = []
        for pdir in sorted(allparents):
            parent_includes.append(f"--include={pdir}/")

        return (
            ["--recursive", "--times"]
            + excludes
            + parent_includes
            + includes
            + ["--exclude=*", src_dir, dest_dir]
        )

    def _get_all_parents(self, dir: str) -> List[str]:
        pdir = Path(dir)
        root = Path("/")
        parents = []
        while pdir != root:
            parents.append(str(pdir))
            pdir = pdir.parent
        return parents


class RestoreActivity(RsyncProgressActivity):
    msg_title = "Restore"
    msg_description = "Copying files from USB stick to Openvario..."
    msg_sync_completed = "Restore has completed."
    msg_sync_cancelled = "Restore was cancelled."
    msg_sync_failed = "Restore has failed (error code: {res})."

    def get_rsync_params(self) -> List[str]:
        mntpoint = self.shell.os.path(USB_MOUNTPOINT)
        dest_dir = self.shell.os.path("//")
        src_dir = os.path.join(mntpoint, "openvario", "backup")
        return ["--recursive", "--times", src_dir + "/", dest_dir]

    def _on_sync_done(self, w: urwid.Widget) -> None:
        # After restore, make sure all files are physically written
        self.shell.os.sync()


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
        super().__init__("pg normal", "pg complete")

    async def start(self) -> None:
        proc = await asyncio.create_subprocess_exec(
            self.os.path(RSYNC_BIN),
            "--info=progress2",
            *self.rsync_params,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            limit=200,
        )

        assert proc.stdout is not None
        assert proc.stderr is not None

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
            self.set_completion(100)
            self._emit("done")
        else:
            errors = await proc.stderr.read()
            self._emit("failed", result, errors.decode())

    def get_text(self) -> str:
        return self._current_progress

    def _set_progress(self, prg: RsyncStatusLine) -> None:
        self.set_completion(prg.progress)
        transferred = format_size(prg.transferred)
        self._current_progress = (
            f"{prg.progress}% | {transferred} | {prg.rate} | {prg.elapsed}"
        )
