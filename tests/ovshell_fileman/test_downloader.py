import asyncio
from pathlib import Path

import urwid
import pytest

from ovshell import testing
from ovshell_fileman.downloader import LogDownloaderActivity


@pytest.fixture
def activity(ovshell: testing.OpenVarioShellStub) -> LogDownloaderActivity:
    ovshell.settings.set("xcsoar.home", "//home/xcsoar")
    return LogDownloaderActivity(ovshell)


def test_activity_fs_not_mounted(
    activity: LogDownloaderActivity, ovshell: testing.OpenVarioShellStub
) -> None:
    w = activity.create()
    rendered = _render(w)
    assert "Please insert USB storage" in rendered


@pytest.mark.asyncio
async def test_activity_list_files(
    activity: LogDownloaderActivity, ovshell: testing.OpenVarioShellStub
) -> None:
    # GIVEN
    _create_sample_filesystem(ovshell)
    w = activity.create()
    activity.activate()

    # WHEN
    # Let mount watcher detect the mount
    await asyncio.sleep(0)
    rendered = _render(w)

    # THEN

    # one.igc is not new - hidden by default
    assert "one.igc" not in rendered
    # two.igc is new - shown
    assert "two.igc" in rendered
    # three.nmea is hidden by default
    assert "three.nmea" not in rendered


def _render(w: urwid.Widget) -> str:
    canvas = w.render((60, 40))
    contents = [t.decode("utf-8") for t in canvas.text]
    return "\n".join(contents)


def _create_sample_filesystem(ovshell: testing.OpenVarioShellStub) -> None:
    rootfs = ovshell.os.path("//")
    Path(rootfs, "dev").mkdir()
    Path(rootfs, "dev", "sda1").touch()
    Path(rootfs, "usb", "usbstick", "logs").mkdir(parents=True)
    Path(rootfs, "usb", "usbstick", "logs", "one.igc").write_bytes(b"1" * 1024)
    Path(rootfs, "home", "xcsoar", "logs").mkdir(parents=True)
    Path(rootfs, "home", "xcsoar", "logs", "one.igc").write_bytes(b"1" * 1024)
    Path(rootfs, "home", "xcsoar", "logs", "two.igc").write_bytes(b"2" * 10000)
    Path(rootfs, "home", "xcsoar", "logs", "three.nmea").write_bytes(b"3" * 100)
