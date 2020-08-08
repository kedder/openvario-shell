from typing import List
import asyncio

import pytest
import urwid

from ovshell import testing

from ovshell_fileman.backupapp import RsyncStatusLine
from ovshell_fileman.backupapp import BackupRestoreApp, BackupRestoreMainActivity

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


def _render(w: urwid.Widget) -> str:
    canvas = w.render((60, 40))
    contents = [t.decode("utf-8") for t in canvas.text]
    return "\n".join(contents)
