import asyncio
from dataclasses import dataclass
from typing import List, Optional

import pytest

from ovshell import testing
from ovshell_fileman.api import Downloader, DownloadFilter, FileInfo, ProgressState
from ovshell_fileman.downloadapp import LogDownloaderActivity, LogDownloaderApp
from tests.fixtures.urwid import UrwidMock

from .stubs import AutomountWatcherStub


class DownloaderStub(Downloader):
    stub_last_filter: Optional[DownloadFilter] = None
    stub_files: Optional[List[FileInfo]] = None
    failing = False

    def list_logs(self, filter: DownloadFilter) -> List[FileInfo]:
        self.stub_last_filter = filter
        return self.stub_files or []

    async def download(self, file: FileInfo, progress: ProgressState) -> None:
        progress.set_total(file.size)
        await asyncio.sleep(0)
        progress.progress(file.size // 2)
        if self.failing:
            raise IOError("Download failed")
        await asyncio.sleep(0)
        progress.progress(file.size // 2)


@dataclass
class LogDownloaderActivityTestbed:
    activity: LogDownloaderActivity

    ovshell: testing.OpenVarioShellStub
    downloader: DownloaderStub
    mountwatcher: AutomountWatcherStub


@pytest.fixture
def activity_testbed(
    ovshell: testing.OpenVarioShellStub,
) -> LogDownloaderActivityTestbed:
    ovshell.settings.set("xcsoar.home", "//home/xcsoar")

    dl = DownloaderStub()
    mw = AutomountWatcherStub()
    act = LogDownloaderActivity(ovshell, mw, dl)
    return LogDownloaderActivityTestbed(act, ovshell, dl, mw)


def test_app_start(ovshell: testing.OpenVarioShellStub) -> None:
    # GIVEN
    ovshell.settings.set("xcsoar.home", "//home/xcsoar")
    app = LogDownloaderApp(ovshell)

    # WHEN
    app.launch()

    # THEN
    act = ovshell.screen.stub_top_activity()
    assert isinstance(act, LogDownloaderActivity)


@pytest.mark.asyncio
async def test_activity_fs_mounting(
    activity_testbed: LogDownloaderActivityTestbed,
) -> None:
    urwid_mock = UrwidMock()
    w = activity_testbed.activity.create()
    activity_testbed.activity.activate()
    await asyncio.sleep(0)
    assert "Please insert USB storage" in urwid_mock.render(w)
    activity_testbed.mountwatcher.stub_device_in()
    assert "Mounting USB storage..." in urwid_mock.render(w)
    activity_testbed.mountwatcher.stub_device_out()
    assert "Please insert USB storage" in urwid_mock.render(w)


@pytest.mark.asyncio
async def test_activity_list_files(
    activity_testbed: LogDownloaderActivityTestbed,
) -> None:
    # GIVEN
    urwid_mock = UrwidMock()
    activity_testbed.downloader.stub_files = [
        FileInfo("two.igc", ".igc", size=20000, mtime=0, downloaded=False)
    ]
    w = activity_testbed.activity.create()
    activity_testbed.activity.activate()

    # Let mount watcher detect start
    await asyncio.sleep(0)
    assert activity_testbed.mountwatcher.stub_running
    activity_testbed.mountwatcher.stub_mount()

    # WHEN
    rendered = urwid_mock.render(w)

    # THEN
    assert "two.igc" in rendered


@pytest.mark.asyncio
async def test_activity_unmount(
    activity_testbed: LogDownloaderActivityTestbed,
) -> None:
    # GIVEN
    urwid_mock = UrwidMock()
    activity_testbed.downloader.stub_files = [
        FileInfo("two.igc", ".igc", size=20000, mtime=0, downloaded=False)
    ]
    w = activity_testbed.activity.create()
    activity_testbed.activity.activate()

    # Let mount watcher detect start
    await asyncio.sleep(0)
    assert activity_testbed.mountwatcher.stub_running
    activity_testbed.mountwatcher.stub_mount()

    assert "two.igc" in urwid_mock.render(w)

    # WHEN
    activity_testbed.mountwatcher.stub_unmount()
    assert "Please insert USB storage" in urwid_mock.render(w)


@pytest.mark.asyncio
async def test_activity_change_settings(
    activity_testbed: LogDownloaderActivityTestbed,
) -> None:
    # GIVEN
    urwid_mock = UrwidMock()
    # Set initial settings
    activity_testbed.ovshell.settings.set(
        "fileman.download_logs.filter", {"new": True, "igc": True, "nmea": True}
    )
    w = activity_testbed.activity.create()
    activity_testbed.activity.activate()
    activity_testbed.mountwatcher.stub_mount()
    await asyncio.sleep(0)

    # WHEN
    # Turn off all settings
    urwid_mock.keypress(w, ["enter", "right", "enter", "right", "enter"])

    # THEN
    filt = activity_testbed.ovshell.settings.get("fileman.download_logs.filter", dict)
    assert filt == {"new": False, "igc": False, "nmea": False}


@pytest.mark.asyncio
async def test_activity_download(
    activity_testbed: LogDownloaderActivityTestbed,
) -> None:
    # GIVEN
    urwid_mock = UrwidMock()
    activity_testbed.downloader.stub_files = [
        FileInfo("two.igc", ".igc", size=20000, mtime=0, downloaded=False)
    ]
    w = activity_testbed.activity.create()
    activity_testbed.activity.activate()
    activity_testbed.mountwatcher.stub_mount()

    # WHEN
    urwid_mock.keypress(w, ["down", "enter"])

    # THEN
    await asyncio.sleep(0)
    assert "0 %" in urwid_mock.render(w)
    await asyncio.sleep(0)
    assert "50 %" in urwid_mock.render(w)
    await asyncio.sleep(0)
    assert "100 %" in urwid_mock.render(w)
    await asyncio.sleep(0)
    assert "Done" in urwid_mock.render(w)


@pytest.mark.asyncio
async def test_activity_download_error(
    activity_testbed: LogDownloaderActivityTestbed,
) -> None:
    # GIVEN
    urwid_mock = UrwidMock()
    activity_testbed.downloader.stub_files = [
        FileInfo("two.igc", ".igc", size=20000, mtime=0, downloaded=False)
    ]
    w = activity_testbed.activity.create()
    activity_testbed.activity.activate()
    activity_testbed.mountwatcher.stub_mount()
    activity_testbed.downloader.failing = True

    # WHEN
    urwid_mock.keypress(w, ["down", "enter"])

    # THEN
    await asyncio.sleep(0)
    assert "0 %" in urwid_mock.render(w)
    await asyncio.sleep(0)
    assert "50 %" in urwid_mock.render(w)
    await asyncio.sleep(0)
    assert "Failed" in urwid_mock.render(w)
