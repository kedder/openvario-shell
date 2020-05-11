from typing import List, Generator, Optional
from pathlib import Path
from dataclasses import dataclass
from contextlib import contextmanager
import asyncio

import pytest

from ovshell_fileman.mountwatch import AutomountWatcherImpl


class MountHandler:
    log: List[str]

    def __init__(self) -> None:
        self.log = []

    def mounted(self) -> None:
        self.log.append("mount")

    def unmounted(self) -> None:
        self.log.append("unmount")


realsleep = asyncio.sleep


async def nosleep(time: float) -> None:
    await realsleep(0)


@dataclass
class AutomountWatcherTestbed:
    watcher: AutomountWatcherImpl
    handler: MountHandler
    device_path: Path
    mount_path: Path

    _task: Optional[asyncio.Task] = None

    @contextmanager
    def started(self) -> Generator[None, None, None]:
        task = asyncio.create_task(self.watcher.run())
        try:
            yield
        finally:
            task.cancel()


@pytest.fixture
def watcher_testbed(tmp_path: Path, monkeypatch) -> AutomountWatcherTestbed:
    root = Path(tmp_path)
    devpath = root / "dev" / "sda1"
    mntpath = root / "usb" / "usbstick"

    devpath.parent.mkdir(parents=True)
    mntpath.parent.mkdir(parents=True)

    handler = MountHandler()
    watcher = AutomountWatcherImpl(str(devpath), str(mntpath))
    watcher.on_mount(handler.mounted)
    watcher.on_unmount(handler.unmounted)

    monkeypatch.setattr("asyncio.sleep", nosleep)

    testbed = AutomountWatcherTestbed(
        watcher, handler, device_path=devpath, mount_path=mntpath
    )

    return testbed


@pytest.mark.asyncio
async def test_mounted_inital(watcher_testbed: AutomountWatcherTestbed) -> None:
    # WHEN
    with watcher_testbed.started():
        await asyncio.sleep(0)

        # THEN
        assert watcher_testbed.handler.log == []


@pytest.mark.asyncio
async def test_mounted_mount(watcher_testbed: AutomountWatcherTestbed) -> None:
    # GIVEN
    with watcher_testbed.started():
        await asyncio.sleep(0)
        watcher_testbed.device_path.touch()

        # WHEN
        watcher_testbed.mount_path.mkdir()
        await asyncio.sleep(0)
        await asyncio.sleep(0)

    # THEN
    assert watcher_testbed.handler.log == ["mount"]


@pytest.mark.asyncio
async def test_mounted_unmounted(watcher_testbed: AutomountWatcherTestbed) -> None:
    # GIVEN
    with watcher_testbed.started():
        await asyncio.sleep(0)
        watcher_testbed.device_path.touch()
        watcher_testbed.mount_path.mkdir()
        await asyncio.sleep(0)

        # WHEN
        watcher_testbed.mount_path.rmdir()
        await asyncio.sleep(0)
        await asyncio.sleep(0)

    # THEN
    assert watcher_testbed.handler.log == ["mount", "unmount"]
