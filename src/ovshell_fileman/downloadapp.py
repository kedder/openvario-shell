from typing import Optional, Dict
import os
import asyncio
import functools

import urwid

from ovshell import protocol
from ovshell import widget

from .api import ProgressState, AutomountWatcher, Downloader, DownloadFilter, FileInfo
from .mountwatch import AutomountWatcherImpl
from .downloader import DownloaderImpl

USB_MOUNTPOINT = "//usb/usbstick"
USB_MOUNTDEVICE = "//dev/sda1"


class ProgressBarState(ProgressState):
    def __init__(self, pb: urwid.ProgressBar) -> None:
        self._pb = pb
        self._completion = 0

    def set_total(self, total: int) -> None:
        self._pb.done = total

    def progress(self, amount: int = 1) -> None:
        self._completion += amount
        self._pb.set_completion(self._completion)


class LogDownloaderApp(protocol.App):
    name = "download-logs"
    title = "Download Logs"
    description = "Download flight logs to USB storage"
    priority = 50

    def __init__(self, shell: protocol.OpenVarioShell):
        self.shell = shell

    def launch(self) -> None:
        act = LogDownloaderActivity(
            self.shell, self._make_mountwatcher(), self._make_downloader()
        )
        self.shell.screen.push_activity(act)

    def _make_mountwatcher(self) -> AutomountWatcher:
        mntdir = self.shell.os.path(USB_MOUNTPOINT)
        mntdev = self.shell.os.path(USB_MOUNTDEVICE)
        return AutomountWatcherImpl(mntdev, mntdir)

    def _make_downloader(self) -> Downloader:
        mntdir = self.shell.os.path(USB_MOUNTPOINT)
        xcsdir = self.shell.os.path(self.shell.settings.getstrict("xcsoar.home", str))
        return DownloaderImpl(os.path.join(xcsdir, "logs"), mntdir)


class LogDownloaderActivity(protocol.Activity):
    _dl_in_progress: Dict[str, urwid.WidgetPlaceholder]
    filter: DownloadFilter

    def __init__(
        self,
        shell: protocol.OpenVarioShell,
        mountwatcher: "AutomountWatcher",
        downloader: "Downloader",
    ) -> None:
        self.shell = shell
        self.mountwatcher = mountwatcher
        self.downloader = downloader
        self._dl_in_progress = {}

    def create(self) -> urwid.Widget:
        filtstate = self.shell.settings.get("fileman.download_logs.filter", dict) or {}
        self.filter = DownloadFilter.fromdict(filtstate)

        self._waiting_text = urwid.Text("Please insert USB storage", align="center")
        self._waiting_view = urwid.Filler(self._waiting_text, "middle")
        self._file_walker = urwid.SimpleFocusListWalker([])
        self._app_view = self._create_app_view()
        self.frame = urwid.Frame(
            self._waiting_view, header=widget.ActivityHeader("Download Flight Logs")
        )
        return self.frame

    def activate(self) -> None:
        self.mountwatcher.on_mount(self._mounted)
        self.mountwatcher.on_unmount(self._unmounted)
        self.mountwatcher.on_device_in(self._device_in)
        self.mountwatcher.on_device_out(self._device_out)
        self.shell.screen.spawn_task(self, self.mountwatcher.run())

    def _create_app_view(self) -> urwid.Widget:
        file_filter = self._make_filter()

        return urwid.Pile(
            [
                ("pack", file_filter),
                ("pack", urwid.Divider()),
                urwid.ListBox(self._file_walker),
            ]
        )

    def _mounted(self) -> None:
        self._populate_file_list()
        self.frame.set_body(self._app_view)
        self._dl_in_progress = {}

    def _unmounted(self) -> None:
        self.frame.set_body(self._waiting_view)

    def _device_in(self) -> None:
        self._waiting_text.set_text("Mounting USB storage...")

    def _device_out(self) -> None:
        self._waiting_text.set_text("Please insert USB storage")

    def _make_filter(self) -> urwid.Widget:
        options = urwid.GridFlow(
            [
                self._make_filter_checkbox("New logs", "new"),
                self._make_filter_checkbox("*.igc", "igc"),
                self._make_filter_checkbox("*.nmea", "nmea"),
            ],
            cell_width=12,
            h_sep=2,
            v_sep=1,
            align="left",
        )
        return urwid.LineBox(options, "Options", title_align="left")

    def _populate_file_list(self) -> None:
        files = self.downloader.list_logs(self.filter)
        if files:
            file_items = [self._make_file_picker(de) for de in files]
        else:
            file_items = [urwid.Text(("remark", "No flight logs selected."))]

        del self._file_walker[:]
        self._file_walker.extend(file_items)
        self._file_walker.set_focus(0)

    def _make_filter_checkbox(self, title: str, attr: str) -> urwid.Widget:
        checked = getattr(self.filter, attr)
        cb = urwid.CheckBox(title, checked)
        urwid.connect_signal(cb, "change", self._set_filter_option, user_args=[attr])
        return cb

    def _set_filter_option(self, attr: str, w: urwid.Widget, state: bool) -> None:
        setattr(self.filter, attr, state)
        self.shell.settings.set("fileman.download_logs.filter", self.filter.asdict())
        self.shell.settings.save()
        self._populate_file_list()

    def _make_file_picker(self, fileinfo: FileInfo) -> urwid.Widget:
        statusw = self._dl_in_progress.get(fileinfo.name)
        if statusw is None:
            st = urwid.Text(" New " if not fileinfo.downloaded else "")
            statusw = urwid.WidgetPlaceholder(st)

        fmtsize = format_size(fileinfo.size)
        cols = urwid.Columns(
            [
                ("weight", 2, urwid.Text(fileinfo.name)),
                ("weight", 1, urwid.Text(fmtsize + " ", align="right")),
                ("weight", 1, statusw),
            ]
        )
        w = SelectableItem(cols)

        urwid.connect_signal(
            w, "click", self._file_clicked, user_args=[fileinfo, statusw]
        )
        return w

    def _file_clicked(
        self, fileinfo: FileInfo, statusw: urwid.WidgetPlaceholder, w: urwid.Widget
    ) -> None:
        if fileinfo.name in self._dl_in_progress:
            # Already in progress, ignore
            return
        self._dl_in_progress[fileinfo.name] = statusw

        pb = urwid.ProgressBar("pg normal", "pg complete")
        statusw.original_widget = pb
        progress = ProgressBarState(pb)

        coro = self.downloader.download(fileinfo, progress)
        task = self.shell.screen.spawn_task(self, coro)
        task.add_done_callback(
            functools.partial(self._download_done, fileinfo, statusw)
        )

    def _download_done(
        self, fileinfo: FileInfo, statusw: urwid.WidgetPlaceholder, task: asyncio.Task
    ) -> None:
        del self._dl_in_progress[fileinfo.name]

        if task.cancelled():
            statusw.original_widget = urwid.Text(("error message", " Cancelled "))
            return
        exc = task.exception()
        if exc is not None:
            statusw.original_widget = urwid.Text(("error banner", " Failed "))
            return

        statusw.original_widget = urwid.Text(("success banner", " Done "))


class SelectableItem(urwid.WidgetWrap):
    signals = ["click"]

    def __init__(self, widget: urwid.Widget) -> None:
        wdg = urwid.AttrMap(widget, "li normal", "li focus")
        super().__init__(wdg)

    def selectable(self):
        return True

    def keypress(self, size, key: str) -> Optional[str]:
        if self._command_map[key] == "activate":
            self._emit("click")
            return None
        return key


def format_size(size: int) -> str:
    fsize = float(size)
    # make suffix the same size to keep numbers dot-aligned
    for unit in ["B  ", "KiB", "MiB", "GiB"]:
        if abs(fsize) < 1024.0:
            return "%3.1f %s" % (fsize, unit)
        fsize /= 1024.0
    return "%.1f %s" % (size, "TiB")
