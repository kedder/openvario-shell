import asyncio
import functools
import os
from typing import Dict, Optional

import urwid

from ovshell import api, widget

from .api import AutomountWatcher, Downloader, DownloadFilter, FileInfo, ProgressState
from .downloader import DownloaderImpl
from .usbcurtain import USBStorageCurtain, make_usbstick_watcher
from .utils import format_size


class ProgressBarState(ProgressState):
    def __init__(self, pb: urwid.ProgressBar) -> None:
        self._pb = pb
        self._completion = 0

    def set_total(self, total: int) -> None:
        self._pb.done = total

    def progress(self, amount: int = 1) -> None:
        self._completion += amount
        self._pb.set_completion(self._completion)


class LogDownloaderApp(api.App):
    name = "download-logs"
    title = "Download Logs"
    description = "Download flight logs to USB storage"
    priority = 50

    def __init__(self, shell: api.OpenVarioShell):
        self.shell = shell

    def launch(self) -> None:
        mountwatcher = make_usbstick_watcher(self.shell.os)
        xcsdir = self.shell.os.path(self.shell.settings.getstrict("xcsoar.home", str))
        mntdir = mountwatcher.get_mountpoint()
        downloader = DownloaderImpl(os.path.join(xcsdir, "logs"), mntdir)

        act = LogDownloaderActivity(self.shell, mountwatcher, downloader)
        self.shell.screen.push_activity(act)


class LogDownloaderActivity(api.Activity):
    _dl_in_progress: Dict[str, urwid.WidgetPlaceholder]
    filter: DownloadFilter

    def __init__(
        self,
        shell: api.OpenVarioShell,
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

        self._file_walker = urwid.SimpleFocusListWalker([])
        self._app_view = self._create_app_view()

        curtain = USBStorageCurtain(self.mountwatcher, self._app_view)
        urwid.connect_signal(curtain, "mounted", self._mounted)

        self.frame = urwid.Frame(
            curtain, header=widget.ActivityHeader("Download Flight Logs")
        )
        return self.frame

    def activate(self) -> None:
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

    def _mounted(self, wdg) -> None:
        self._populate_file_list()
        self._dl_in_progress = {}

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
        w = widget.SelectableItem(cols)

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
