from typing import Callable, List
import os
import asyncio

from .api import AutomountWatcher


class AutomountWatcherImpl(AutomountWatcher):
    _mount_handlers: List[Callable[[], None]]
    _unmount_handlers: List[Callable[[], None]]

    def __init__(self, device: str, mountpoint: str) -> None:
        self._mountdev = device
        self._mountpoint = mountpoint
        self._mount_handlers = []
        self._unmount_handlers = []
        self._mounted = False

    async def run(self) -> None:
        while True:
            # Make sure device appearsh before trying to poll the mount point.
            # Otherwise autofs will not mount the device.
            await self._wait_for_device()

            if os.path.exists(self._mountpoint):
                self._online()
            else:
                self._offline()
            await asyncio.sleep(1)

    def on_mount(self, handler: Callable[[], None]) -> None:
        self._mount_handlers.append(handler)

    def on_unmount(self, handler: Callable[[], None]) -> None:
        self._unmount_handlers.append(handler)

    async def _wait_for_device(self):
        while True:
            if os.path.exists(self._mountdev):
                break
            self._offline()
            await asyncio.sleep(1)

    def _online(self) -> None:
        if self._mounted:
            return
        self._mounted = True
        for handler in self._mount_handlers:
            handler()

    def _offline(self) -> None:
        if not self._mounted:
            return
        self._mounted = False
        for handler in self._unmount_handlers:
            handler()
