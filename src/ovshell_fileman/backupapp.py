from typing import List, Optional, Coroutine
import os
import re
import asyncio
from abc import abstractmethod
from pathlib import Path

import urwid

from ovshell import api
from ovshell import widget

from .api import AutomountWatcher, RsyncRunner, RsyncStatusLine, RsyncFailedException
from .rsync import RsyncRunnerImpl
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


class BackupRestoreApp(api.App):
    name = "backup"
    title = "Backup"
    description = "Copy files to and from USB stick"
    priority = 40

    def __init__(self, shell: api.OpenVarioShell):
        self.shell = shell

    def launch(self) -> None:
        rsync = RsyncRunnerImpl(self.shell.os.path(RSYNC_BIN))
        act = BackupRestoreMainActivity(
            self.shell, make_usbstick_watcher(self.shell.os), rsync
        )
        self.shell.screen.push_activity(act)


class BackupRestoreMainActivity(api.Activity):
    def __init__(
        self,
        shell: api.OpenVarioShell,
        mountwatcher: AutomountWatcher,
        rsync: RsyncRunner,
    ) -> None:
        self.shell = shell
        self.mountwatcher = mountwatcher
        self.rsync = rsync

    def create(self) -> urwid.Widget:
        intro = urwid.Text(
            [
                (
                    "remark",
                    "This app allows to copy files to and from USB stick directory ",
                ),
                BACKUP_DEST,
                ("remark", "."),
            ]
        )
        backup_help = urwid.Text(
            "The following directories will be copied to USB stick:"
        )

        backupdirs = urwid.Pile([urwid.Text(f"  * {d}") for d in BACKUP_DIRS])
        self.restoredirs = urwid.Pile([])

        b_backup = widget.PlainButton("Backup")
        urwid.connect_signal(b_backup, "click", self._on_backup)

        b_restore = widget.PlainButton("Restore")
        urwid.connect_signal(b_restore, "click", self._on_restore)

        restore_help = urwid.Text(
            "The following directories will be copied from USB stick "
            "to root filesystem:"
        )

        self._app_view = urwid.Filler(
            urwid.Pile(
                [
                    intro,
                    urwid.Divider(),
                    backup_help,
                    urwid.Divider(),
                    backupdirs,
                    urwid.Divider(),
                    self._button_grid([b_backup]),
                    urwid.Divider(),
                    restore_help,
                    urwid.Divider(),
                    self.restoredirs,
                    urwid.Divider(),
                    self._button_grid([b_restore]),
                ]
            ),
            "top",
        )

        curtain = USBStorageCurtain(self.mountwatcher, self._app_view)
        urwid.connect_signal(curtain, "mounted", self._on_mounted)

        self.frame = urwid.Frame(
            curtain, header=widget.ActivityHeader("Backup & Restore")
        )
        return self.frame

    def show(self) -> None:
        self._refresh_restore_dirs()

    def activate(self) -> None:
        self.shell.screen.spawn_task(self, self.mountwatcher.run())

    def _button_grid(self, buttons: List[urwid.Widget]) -> urwid.GridFlow:
        return urwid.GridFlow(buttons, cell_width=15, h_sep=1, v_sep=1, align="left",)

    def _on_backup(self, w: urwid.Widget) -> None:
        act = BackupActivity(self.shell, self.rsync)
        self.shell.screen.push_modal(act, self._get_rsync_modal_opts())

    def _on_restore(self, w: urwid.Widget) -> None:
        act = RestoreActivity(self.shell, self.rsync)
        self.shell.screen.push_modal(act, self._get_rsync_modal_opts())

    def _on_mounted(self, w: urwid.Widget) -> None:
        self._refresh_restore_dirs()

    def _get_rsync_modal_opts(self) -> api.ModalOptions:
        return api.ModalOptions(
            align="center", width=("relative", 80), valign="middle", height="pack",
        )

    def _refresh_restore_dirs(self) -> None:
        mntpoint = self.shell.os.path(USB_MOUNTPOINT)
        if not os.path.exists(mntpoint):
            return

        backup_dir = os.path.join(mntpoint, BACKUP_DEST)
        if not os.path.exists(backup_dir):
            msg = f"{BACKUP_DEST} does not exist on USB stick."
            wdg = urwid.Text([("remark",)])
            self.restoredirs.contents = [(wdg, ("pack", None))]
            return

        dirs = os.listdir(backup_dir)
        if not dirs:
            wdg = urwid.Text([("remark", f"No files to restore.")])
            self.restoredirs.contents = [(wdg, ("pack", None))]
            return

        restoredir_contents = []
        for rdir in os.listdir(backup_dir):
            restoredir_contents.append((urwid.Text(f"  * {rdir}"), ("pack", None)))

        self.restoredirs.contents = restoredir_contents


class RsyncProgressActivity(api.Activity):
    rsync_task: Optional["asyncio.Task[int]"] = None

    msg_title: str
    msg_description: str
    msg_sync_completed: str
    msg_sync_cancelled: str
    msg_sync_failed: str

    def __init__(self, shell: api.OpenVarioShell, rsync: RsyncRunner) -> None:
        self.shell = shell
        self.rsync = rsync

    @abstractmethod
    def get_rsync_params(self) -> List[str]:
        pass

    def create(self) -> None:
        self._progress = RsyncProgressBar(
            self.shell.os, self.get_rsync_params(), self.rsync
        )
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
        dest_dir = os.path.join(mntpoint, BACKUP_DEST)
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
        src_dir = os.path.join(mntpoint, BACKUP_DEST)
        return ["--recursive", "--times", src_dir + "/", dest_dir]

    def _on_sync_done(self, w: urwid.Widget) -> None:
        super()._on_sync_done(w)
        # After restore, make sure all files are physically written
        self.shell.os.sync()


class RsyncProgressBar(urwid.ProgressBar):
    signals = ["done", "failed"]

    def __init__(
        self, os: api.OpenVarioOS, rsync_params: List[str], rsync: RsyncRunner
    ) -> None:
        self.os = os
        self.rsync = rsync
        self.rsync_params = rsync_params
        self._current_progress = ""
        super().__init__("pg normal", "pg complete")

    async def start(self) -> None:
        try:
            async for rsync_progress in self.rsync.run(self.rsync_params):
                self._set_progress(rsync_progress)

            self.set_completion(100)
            self._emit("done")
        except RsyncFailedException as e:
            self._emit("failed", e.returncode, e.errors)

    def get_text(self) -> str:
        return self._current_progress

    def _set_progress(self, prg: RsyncStatusLine) -> None:
        self.set_completion(prg.progress)
        transferred = format_size(prg.transferred)
        self._current_progress = (
            f"{prg.progress}% | {transferred} | {prg.rate} | {prg.elapsed}"
        )
