from typing import Callable, List
import os
import asyncio

import urwid

from ovshell import protocol

USB_MOUNTPOINT = "//usb/usbstick"


class LogDownloaderApp(protocol.App):
    name = "download-logs"
    title = "Download Logs"
    description = "Download flight logs to USB storage"
    priority = 50

    def __init__(self, shell: protocol.OpenVarioShell):
        self.shell = shell

    def launch(self) -> None:
        act = LogDownloaderActivity(self.shell)
        self.shell.screen.push_activity(act)


class LogDownloaderActivity(protocol.Activity):
    def __init__(self, shell: protocol.OpenVarioShell):
        self.shell = shell
        self.mountwatcher = AutomountWatcher(shell.os.path(USB_MOUNTPOINT))

    def create(self) -> urwid.Widget:
        return urwid.Filler(
            urwid.Padding(urwid.Text("Hello World!"), width=30, align="center")
        )

    def activate(self) -> None:
        self.mountwatcher.on_mount(self._mounted)
        self.mountwatcher.on_unmount(self._unmounted)
        self.shell.screen.spawn_task(self, self.mountwatcher.run())

    def _mounted(self) -> None:
        print("MOUNTED")

    def _unmounted(self) -> None:
        print("UNMOUNTED")


class AutomountWatcher:
    _mount_handlers: List[Callable[[], None]]
    _unmount_handlers: List[Callable[[], None]]

    def __init__(self, mountpoint: str) -> None:
        self._mountpoint = mountpoint
        self._mount_handlers = []
        self._unmount_handlers = []

    async def run(self) -> None:
        mounted = False
        while True:
            if os.path.exists(self._mountpoint):
                if not mounted:
                    self._handle_mount()
                mounted = True
            else:
                if mounted:
                    self._handle_unmount()
                mounted = False
            await asyncio.sleep(1)

    def on_mount(self, handler: Callable[[], None]) -> None:
        self._mount_handlers.append(handler)

    def on_unmount(self, handler: Callable[[], None]) -> None:
        self._unmount_handlers.append(handler)

    def _handle_mount(self) -> None:
        for handler in self._mount_handlers:
            handler()

    def _handle_unmount(self) -> None:
        for handler in self._unmount_handlers:
            handler()
