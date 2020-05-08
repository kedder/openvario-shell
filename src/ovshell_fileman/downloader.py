from typing import Callable, List, Optional, Dict, Any
from typing_extensions import Protocol
import os
import asyncio
import functools
from abc import abstractmethod
from dataclasses import dataclass, asdict

import urwid

from ovshell import protocol
from ovshell import widget

USB_MOUNTPOINT = "//usb/usbstick"
USB_MOUNTDEVICE = "//dev/sda1"


@dataclass
class DownloadFilter:
    new: bool = True
    igc: bool = True
    nmea: bool = False

    def asdict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def fromdict(cls, state: Dict[str, Any]) -> "DownloadFilter":
        filt = cls()
        if "new" in state:
            filt.new = state["new"]
        if "igc" in state:
            filt.igc = state["igc"]
        if "nmea" in state:
            filt.nmea = state["nmea"]
        return filt


@dataclass
class FileInfo:
    name: str
    ftype: str
    size: int
    mtime: float
    downloaded: bool


class ProgressState(Protocol):
    @abstractmethod
    def set_total(self, total: int) -> None:
        pass  # pragma: nocover

    @abstractmethod
    def progress(self, amount: int = 1) -> None:
        pass  # pragma: nocover


class Downloader(Protocol):
    @abstractmethod
    def list_logs(self, filter: DownloadFilter) -> List[FileInfo]:
        pass  # pragma: nocover

    @abstractmethod
    async def download(self, file: FileInfo, progress: ProgressState) -> None:
        pass  # pragma: nocover


class AutomountWatcher(Protocol):
    @abstractmethod
    def on_unmount(self, handler: Callable[[], None]) -> None:
        pass  # pragma: nocover

    @abstractmethod
    def on_mount(self, handler: Callable[[], None]) -> None:
        pass  # pragma: nocover

    @abstractmethod
    async def run(self) -> None:
        pass  # pragma: nocover


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
        filtstate = self.shell.settings.get("fileman.download-logs.filter", dict) or {}
        self.filter = DownloadFilter.fromdict(filtstate)

        self._waiting_view = urwid.Filler(
            urwid.Text("Please insert USB storage", align="center"), "middle"
        )
        self._file_walker = urwid.SimpleFocusListWalker([])
        self._app_view = self._create_app_view()
        self.frame = urwid.Frame(
            self._waiting_view, header=widget.ActivityHeader("Download Flight Logs")
        )
        return self.frame

    def activate(self) -> None:
        self.mountwatcher.on_mount(self._mounted)
        self.mountwatcher.on_unmount(self._unmounted)
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
        self.shell.settings.set("fileman.download-logs.filter", self.filter.asdict())
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


class DownloaderImpl(Downloader):
    """Object that handles file copying and listing"""

    def __init__(self, source_dir: str, mount_dir: str) -> None:
        self.source_dir = source_dir
        self.mount_dir = mount_dir

    def list_logs(self, filter: DownloadFilter) -> List[FileInfo]:
        if not os.path.exists(self.source_dir):
            return []
        downloaded = self._find_downloaded()
        res = []
        for entry in os.scandir(self.source_dir):
            _, fext = os.path.splitext(entry.name.lower())
            fileinfo = FileInfo(
                name=entry.name,
                ftype=fext,
                size=entry.stat().st_size,
                mtime=entry.stat().st_mtime,
                downloaded=entry.name.lower() in downloaded,
            )
            if self._matches(fileinfo, filter):
                res.append(fileinfo)
        return sorted(res, key=lambda fi: fi.mtime, reverse=True)

    async def download(self, file: FileInfo, progress: ProgressState) -> None:
        destdir = self._ensure_dest_dir()
        srcfile = os.path.join(self.source_dir, file.name)
        dstfile = os.path.join(destdir, file.name)

        # Copying large files can take a long time and the process can fail at
        # any time. To avoid leaving incompletely downloaded file, we copy
        # contents into temporary file, and rename it after copy completed.
        tmpdstfile = dstfile + ".partial"
        chunksize = 1024 * 4

        progress.set_total(file.size)
        with open(srcfile, "rb") as sf, open(tmpdstfile, "wb") as df:
            while True:
                chunk = sf.read(chunksize)
                if len(chunk) == 0:
                    break
                df.write(chunk)
                progress.progress(len(chunk))
                await asyncio.sleep(0)

        # Finally, rename the file
        os.replace(tmpdstfile, dstfile)
        os.sync()

    def _matches(self, fileinfo: FileInfo, filter: DownloadFilter) -> bool:
        ftypes = [".nmea" if filter.nmea else None, ".igc" if filter.igc else None]
        matches = fileinfo.ftype in ftypes
        if filter.new:
            matches = matches and not fileinfo.downloaded
        return matches

    def _find_downloaded(self) -> List[str]:
        destdir = self._get_dest_dir()
        if not os.path.exists(destdir):
            return []

        return [fn.lower() for fn in os.listdir(destdir)]

    def _ensure_dest_dir(self) -> str:
        assert os.path.exists(self.mount_dir)
        destdir = self._get_dest_dir()
        os.makedirs(destdir, exist_ok=True)
        return destdir

    def _get_dest_dir(self) -> str:
        return os.path.join(self.mount_dir, "logs")


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
