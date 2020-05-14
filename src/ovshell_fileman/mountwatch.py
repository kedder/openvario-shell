from typing import Callable, List
import os
import asyncio

from .api import AutomountWatcher


class AutomountWatcherImpl(AutomountWatcher):
    _mount_handlers: List[Callable[[], None]]
    _unmount_handlers: List[Callable[[], None]]
    _device_in_handlers: List[Callable[[], None]]
    _device_out_handlers: List[Callable[[], None]]

    def __init__(self, device: str, mountpoint: str) -> None:
        self._mountdev = device
        self._mountpoint = mountpoint
        self._mount_handlers = []
        self._unmount_handlers = []
        self._device_in_handlers = []
        self._device_out_handlers = []

        self._device = False
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

    async def _wait_for_device(self):
        while True:
            if os.path.exists(self._mountdev):
                self._device_in()
                break
            self._device_out()
            self._offline()
            await asyncio.sleep(1)

    def on_device_in(self, handler: Callable[[], None]):
        self._device_in_handlers.append(handler)

    def on_device_out(self, handler: Callable[[], None]):
        self._device_out_handlers.append(handler)

    def on_mount(self, handler: Callable[[], None]) -> None:
        self._mount_handlers.append(handler)

    def on_unmount(self, handler: Callable[[], None]) -> None:
        self._unmount_handlers.append(handler)

    def _device_in(self) -> None:
        if self._device:
            return
        self._device = True
        for handler in self._device_in_handlers:
            handler()

    def _device_out(self) -> None:
        if not self._device:
            return
        self._device = False
        for handler in self._device_out_handlers:
            handler()

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
