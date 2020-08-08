from typing import List, Tuple
import asyncio

import pytest
import urwid

from ovshell import testing

from ovshell_fileman.api import RsyncStatusLine
from ovshell_fileman.backupapp import BackupRestoreApp, BackupRestoreMainActivity
from ovshell_fileman.backupapp import BackupActivity, RestoreActivity

from .stubs import AutomountWatcherStub, RsyncRunnerStub, BackupDirectoryStub


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


def _render(w: urwid.Widget) -> str:
    size: Tuple[int, ...] = (60, 40)
    if "flow" in w.sizing():
        size = (60,)
    canvas = w.render(size)
    contents = [t.decode("utf-8") for t in canvas.text]
    return "\n".join(contents)


def _keypress(w: urwid.Widget, keys: List[str]) -> None:
    for key in keys:
        nothandled = w.keypress((60, 40), key)
        assert nothandled is None
