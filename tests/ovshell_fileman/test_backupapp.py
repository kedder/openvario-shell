import asyncio

import pytest
import urwid

from ovshell import testing

from ovshell_fileman.backupapp import RsyncStatusLine
from ovshell_fileman.backupapp import BackupRestoreApp, BackupRestoreMainActivity

from .stubs import AutomountWatcherStub


def test_rsync_progress_parse_malformed() -> None:
    # GIVEN
    line = b"               \r"

    # WHEN
    sl = RsyncStatusLine.parse(line)

    # THEN
    assert sl is None


def test_rsync_progress_parse1() -> None:
    # GIVEN
    line = b"              0   0%    0.00kB/s    0:00:00 (xfr#0, ir-chk=1006/1007) \r"

    # WHEN
    sl = RsyncStatusLine.parse(line)

    # THEN
    assert sl is not None
    assert sl.transferred == 0
    assert sl.progress == 0
    assert sl.rate == "0.00kB/s"
    assert sl.elapsed == "0:00:00"
    assert sl.xfr == "xfr#0, ir-chk=1006/1007"


def test_rsync_progress_parse2() -> None:
    # GIVEN
    line = b"  1,112,343,559  42%  265.39MB/s    0:00:05   \r"

    # WHEN
    sl = RsyncStatusLine.parse(line)

    # THEN
    assert sl is not None
    assert sl.transferred == 1112343559
    assert sl.progress == 42
    assert sl.rate == "265.39MB/s"
    assert sl.elapsed == "0:00:05"
    assert sl.xfr is None


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
    mountwatcher = AutomountWatcherStub()
    act = BackupRestoreMainActivity(ovshell, mountwatcher)
    w = act.create()
    act.activate()
    act.show()
    await asyncio.sleep(0)
    assert "Please insert USB storage" in _render(w)
    mountwatcher.stub_mount()
    await asyncio.sleep(0)
    assert "This app allows to copy files to and from USB stick" in _render(w)


def _render(w: urwid.Widget) -> str:
    canvas = w.render((60, 40))
    contents = [t.decode("utf-8") for t in canvas.text]
    return "\n".join(contents)
