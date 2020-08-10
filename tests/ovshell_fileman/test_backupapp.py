from typing import List, Tuple
import os
import asyncio
from pathlib import Path

import pytest
import urwid

from ovshell import testing

from ovshell_fileman.api import RsyncStatusLine, RsyncFailedException
from ovshell_fileman.backupapp import BackupRestoreApp, BackupRestoreMainActivity
from ovshell_fileman.backupapp import BackupActivity, RestoreActivity
from ovshell_fileman.backupapp import BackupDirectoryImpl

from .stubs import AutomountWatcherStub, RsyncRunnerStub, BackupDirectoryStub


class TestBackupDirectoryImpl:
    def test_ensure_backup_destination(self, tmp_path: Path) -> None:
        backupdir = BackupDirectoryImpl(str(tmp_path))
        backuppath = backupdir.ensure_backup_destination()
        assert os.path.exists(backuppath)

    def test_get_backup_destination(self, tmp_path: Path) -> None:
        backupdir = BackupDirectoryImpl(str(tmp_path))
        backuppath = backupdir.get_backup_destination()
        assert Path(backuppath) == tmp_path.joinpath("openvario", "backup")

    def test_get_backed_up_files_no_dir(self) -> None:
        backupdir = BackupDirectoryImpl("/not/existing/dir")
        assert backupdir.get_backed_up_files() == []

    def test_get_backed_up_files_empty(self, tmp_path: Path) -> None:
        backupdir = BackupDirectoryImpl(str(tmp_path))
        assert backupdir.get_backed_up_files() == []

    def test_get_backed_up_files_simple(self, tmp_path: Path) -> None:
        # GIVEN
        backupdir = BackupDirectoryImpl(str(tmp_path))
        backuppath = Path(backupdir.ensure_backup_destination())
        backuppath.joinpath("one.txt").touch()
        backuppath.joinpath("subdir").mkdir()

        # WHEN
        files = backupdir.get_backed_up_files()

        # THEN
        assert files == ["one.txt", "subdir"]


def test_app_start(ovshell: testing.OpenVarioShellStub) -> None:
    # GIVEN
    app = BackupRestoreApp(ovshell)

    # WHEN
    app.launch()

    # THEN
    act = ovshell.screen.stub_top_activity()
    assert isinstance(act, BackupRestoreMainActivity)


@pytest.mark.asyncio
async def test_activity_mounting(ovshell: testing.OpenVarioShellStub) -> None:
    # GIVEN
    mountwatcher = AutomountWatcherStub()
    rsync = RsyncRunnerStub()
    backupdir = BackupDirectoryStub()
    act = BackupRestoreMainActivity(ovshell, mountwatcher, rsync, backupdir)
    w = act.create()
    act.activate()
    act.show()

    await asyncio.sleep(0)
    assert "Please insert USB storage" in _render(w)

    # WHEN
    mountwatcher.stub_mount()
    await asyncio.sleep(0)

    # THEN
    assert "This app allows to copy files to and from USB stick" in _render(w)
    assert "No files to restore." in _render(w)

    # WHEN
    backupdir.backed_up_files = ["file_one", "file_two"]
    act.show()
    assert "file_one" in _render(w)
    assert "file_two" in _render(w)


@pytest.mark.asyncio
async def test_activity_backup(ovshell: testing.OpenVarioShellStub) -> None:
    # GIVEN
    mountwatcher = AutomountWatcherStub()
    rsync = RsyncRunnerStub()
    backupdir = BackupDirectoryStub()
    act = BackupRestoreMainActivity(ovshell, mountwatcher, rsync, backupdir)
    w = act.create()
    act.activate()
    mountwatcher.stub_mount()

    # WHEN
    # Press the default button (Backup)
    assert "Backup" in _render(w)
    _keypress(w, ["enter"])

    # THEN
    pact = ovshell.screen.stub_top_activity()
    assert isinstance(pact, BackupActivity)


@pytest.mark.asyncio
async def test_activity_restore(ovshell: testing.OpenVarioShellStub) -> None:
    # GIVEN
    mountwatcher = AutomountWatcherStub()
    rsync = RsyncRunnerStub()
    backupdir = BackupDirectoryStub()
    act = BackupRestoreMainActivity(ovshell, mountwatcher, rsync, backupdir)
    w = act.create()
    act.activate()
    mountwatcher.stub_mount()

    # WHEN
    # Press the default button (Backup)
    assert "Backup" in _render(w)
    _keypress(w, ["down", "enter"])

    # THEN
    pact = ovshell.screen.stub_top_activity()
    assert isinstance(pact, RestoreActivity)


@pytest.mark.asyncio
async def test_backup_act_create(ovshell: testing.OpenVarioShellStub) -> None:
    # GIVEN
    rsync = RsyncRunnerStub()
    act = BackupActivity(ovshell, rsync, "/backup_src", "/backup_dest")

    # WHEN
    w = act.create()

    # THEN
    rendered = _render(w)
    assert "Backup" in rendered
    assert "Copying files from Openvario to USB stick..." in rendered
    assert "Cancel" in rendered


def test_backup_act_get_rsync_args(ovshell: testing.OpenVarioShellStub) -> None:
    # GIVEN
    rsync = RsyncRunnerStub()
    act = BackupActivity(ovshell, rsync, "/backup_src", "/backup_dest")

    # WHEN
    params = act.get_rsync_params()

    # THEN
    assert params == [
        "--recursive",
        "--times",
        "--exclude=/home/root/.profile",
        "--exclude=/home/root/.cache",
        "--include=/etc/",
        "--include=/etc/dropbear/",
        "--include=/etc/opkg/",
        "--include=/home/",
        "--include=/home/root/",
        "--include=/opt/",
        "--include=/opt/conf/",
        "--include=/var/",
        "--include=/var/lib/",
        "--include=/var/lib/connman/",
        "--include=/home/root/**",
        "--include=/var/lib/connman/**",
        "--include=/etc/opkg/**",
        "--include=/etc/dropbear/**",
        "--include=/opt/conf/**",
        "--exclude=*",
        "/backup_src",
        "/backup_dest",
    ]


def test_restore_act_get_rsync_args(ovshell: testing.OpenVarioShellStub) -> None:
    # GIVEN
    rsync = RsyncRunnerStub()
    act = RestoreActivity(ovshell, rsync, "/backup_src", "/backup_dest")

    # WHEN
    params = act.get_rsync_params()

    # THEN
    assert params == [
        "--recursive",
        "--times",
        "/backup_dest/",
        "/backup_src",
    ]


@pytest.mark.asyncio
async def test_restore_show_progress(ovshell: testing.OpenVarioShellStub) -> None:
    rsync = RsyncRunnerStub()
    rsync.progress = [
        RsyncStatusLine(0, 0, "0 KB/s", "00:01:00", None),
        RsyncStatusLine(2000, 23, "15 KB/s", "01:28:20", None),
        RsyncStatusLine(12000, 85, "12 KB/s", "03:29:12", None),
    ]
    act = RestoreActivity(ovshell, rsync, "/backup_src", "/backup_dest")
    ovshell.screen.push_activity(act)

    w = act.create()
    act.activate()

    await asyncio.sleep(0)
    assert "0% | 0.0 B   | 0 KB/s | 00:01:00" in _render(w)
    await asyncio.sleep(0)
    assert "23% | 2.0 KiB | 15 KB/s | 01:28:20" in _render(w)
    await asyncio.sleep(0)
    assert "85% | 11.7 KiB | 12 KB/s | 03:29:12" in _render(w)
    await asyncio.sleep(0)
    assert "Restore has completed." in _render(w)
    assert "Close" in _render(w)

    _keypress(w, ["enter"])
    assert ovshell.screen.stub_top_activity() == None


@pytest.mark.asyncio
async def test_restore_cancel(ovshell: testing.OpenVarioShellStub) -> None:
    rsync = RsyncRunnerStub()
    rsync.progress = [
        RsyncStatusLine(0, 0, "0 KB/s", "00:01:00", None),
        RsyncStatusLine(2000, 23, "15 KB/s", "01:28:20", None),
        RsyncStatusLine(12000, 85, "12 KB/s", "03:29:12", None),
    ]
    act = RestoreActivity(ovshell, rsync, "/backup_src", "/backup_dest")
    ovshell.screen.push_activity(act)

    w = act.create()
    act.activate()

    await asyncio.sleep(0)
    assert "0% | 0.0 B   | 0 KB/s | 00:01:00" in _render(w)
    await asyncio.sleep(0)

    # press the cancel button
    assert "Cancel" in _render(w)
    _keypress(w, ["enter"])

    await asyncio.sleep(0)
    assert "Restore was cancelled." in _render(w)

    # close the activity
    assert "Close" in _render(w)
    _keypress(w, ["enter"])
    assert ovshell.screen.stub_top_activity() == None


@pytest.mark.asyncio
async def test_restore_failure(ovshell: testing.OpenVarioShellStub) -> None:
    rsync = RsyncRunnerStub()
    rsync.progress = [
        RsyncStatusLine(0, 0, "0 KB/s", "00:01:00", None),
        RsyncFailedException(255, "Expected failure"),
    ]
    act = RestoreActivity(ovshell, rsync, "/backup_src", "/backup_dest")
    ovshell.screen.push_activity(act)

    w = act.create()
    act.activate()

    await asyncio.sleep(0)
    assert "0% | 0.0 B   | 0 KB/s | 00:01:00" in _render(w)
    await asyncio.sleep(0)

    # rsync should fail at this point
    assert "Restore has failed (error code: 255)." in _render(w)
    assert "Expected failure" in _render(w)

    # close the activity
    assert "Close" in _render(w)
    _keypress(w, ["enter"])
    assert ovshell.screen.stub_top_activity() == None


def _render(w: urwid.Widget) -> str:
    canvas = w.render(_get_size(w))
    contents = [t.decode("utf-8") for t in canvas.text]
    return "\n".join(contents)


def _keypress(w: urwid.Widget, keys: List[str]) -> None:
    for key in keys:
        nothandled = w.keypress(_get_size(w), key)
        assert nothandled is None


def _get_size(w: urwid.Widget) -> Tuple[int, ...]:
    size: Tuple[int, ...] = (60, 40)
    if "flow" in w.sizing():
        size = (60,)
    return size
