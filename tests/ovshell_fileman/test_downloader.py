from typing import Callable, List, Optional
import asyncio
from dataclasses import dataclass

import urwid
import pytest

from ovshell import testing
from ovshell_fileman.downloader import LogDownloaderActivity, LogDownloaderApp
from ovshell_fileman.downloader import (
    Downloader,
    AutomountWatcher,
    DownloadFilter,
    FileInfo,
    ProgressState,
)


class DownloaderStub(Downloader):
    stub_last_filter: Optional[DownloadFilter] = None
    stub_files: Optional[List[FileInfo]] = None

    def list_logs(self, filter: DownloadFilter) -> List[FileInfo]:
        self.stub_last_filter = filter
        return self.stub_files or []

    async def download(self, file: FileInfo, progress: ProgressState) -> None:
        pass


class AutomountWatcherStub(AutomountWatcher):
    stub_running = False

    _mount_handlers: List[Callable[[], None]]
    _unmount_handlers: List[Callable[[], None]]

    def __init__(self):
        self._mount_handlers = []
        self._unmount_handlers = []

    def on_unmount(self, handler: Callable[[], None]) -> None:
        self._unmount_handlers.append(handler)

    def on_mount(self, handler: Callable[[], None]) -> None:
        self._mount_handlers.append(handler)

    async def run(self) -> None:
        self.stub_running = True

    def stub_mount(self) -> None:
        for h in self._mount_handlers:
            h()

    def stub_unmount(self) -> None:
        for h in self._unmount_handlers:
            h()


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


def test_activity_fs_not_mounted(
    activity_testbed: LogDownloaderActivityTestbed,
) -> None:
    w = activity_testbed.activity.create()
    rendered = _render(w)
    assert "Please insert USB storage" in rendered


@pytest.mark.asyncio
async def test_activity_list_files(
    activity_testbed: LogDownloaderActivityTestbed,
) -> None:
    # GIVEN
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
    rendered = _render(w)

    # THEN
    assert "two.igc" in rendered


@pytest.mark.asyncio
async def test_activity_change_settings(
    activity_testbed: LogDownloaderActivityTestbed,
) -> None:
    # GIVEN
    # Set initial settings
    activity_testbed.ovshell.settings.set(
        "fileman.download-logs.filter", {"new": True, "igc": True, "nmea": True}
    )
    w = activity_testbed.activity.create()
    activity_testbed.activity.activate()
    activity_testbed.mountwatcher.stub_mount()
    await asyncio.sleep(0)

    # WHEN
    # Turn off all settings
    _keypress(w, ["enter", "right", "enter", "right", "enter"])

    # THEN
    filt = activity_testbed.ovshell.settings.get("fileman.download-logs.filter", dict)
    assert filt == {"new": False, "igc": False, "nmea": False}


@pytest.mark.asyncio
async def test_activity_download(
    activity_testbed: LogDownloaderActivityTestbed,
) -> None:
    # GIVEN
    activity_testbed.downloader.stub_files = [
        FileInfo("two.igc", ".igc", size=20000, mtime=0, downloaded=False)
    ]
    w = activity_testbed.activity.create()
    activity_testbed.activity.activate()
    activity_testbed.mountwatcher.stub_mount()

    # WHEN
    _keypress(w, ["down", "enter"])

    # THEN
    await asyncio.sleep(0)
    rendered = _render(w)
    assert "0 %" in rendered

    # WHEN
    await asyncio.sleep(0)
    rendered = _render(w)
    assert "Done" in rendered


def _render(w: urwid.Widget) -> str:
    canvas = w.render((60, 40))
    contents = [t.decode("utf-8") for t in canvas.text]
    return "\n".join(contents)


def _keypress(w: urwid.Widget, keys: List[str]) -> None:
    for key in keys:
        nothandled = w.keypress((60, 40), key)
        assert nothandled is None
