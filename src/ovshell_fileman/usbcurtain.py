import urwid

from ovshell import api

from .api import AutomountWatcher
from .mountwatch import AutomountWatcherImpl

USB_MOUNTPOINT = "//usb/usbstick"
USB_MOUNTDEVICE = "//dev/sda1"


def make_usbstick_watcher(os: api.OpenVarioOS) -> AutomountWatcher:
    mntdir = os.path(USB_MOUNTPOINT)
    mntdev = os.path(USB_MOUNTDEVICE)
    return AutomountWatcherImpl(mntdev, mntdir)


class USBStorageCurtain(urwid.WidgetWrap):
    signals = ["mounted", "unmounted"]

    def __init__(
        self, mountwatcher: AutomountWatcher, mounted_widget: urwid.Widget
    ) -> None:
        self.mountwatcher = mountwatcher

        self._waiting_text = urwid.Text("Please insert USB storage", align="center")
        self._waiting_view = urwid.Filler(self._waiting_text, "middle")
        self._mounted_widget = mounted_widget

        mountwatcher.on_mount(self._mounted)
        mountwatcher.on_unmount(self._unmounted)
        mountwatcher.on_device_in(self._device_in)
        mountwatcher.on_device_out(self._device_out)

        super().__init__(self._waiting_view)

    def _mounted(self) -> None:
        self._w = self._mounted_widget
        self._emit("mounted")

    def _unmounted(self) -> None:
        self._w = self._waiting_view
        self._emit("unmounted")

    def _device_in(self) -> None:
        self._waiting_text.set_text("Mounting USB storage...")

    def _device_out(self) -> None:
        self._waiting_text.set_text("Please insert USB storage")
