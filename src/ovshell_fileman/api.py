from typing import Callable, List, Dict, Any
from typing_extensions import Protocol
from abc import abstractmethod
from dataclasses import dataclass, asdict


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
    def on_device_in(self, handler: Callable[[], None]):
        pass  # pragma: nocover

    @abstractmethod
    def on_device_out(self, handler: Callable[[], None]):
        pass  # pragma: nocover

    @abstractmethod
    def on_unmount(self, handler: Callable[[], None]) -> None:
        pass  # pragma: nocover

    @abstractmethod
    def on_mount(self, handler: Callable[[], None]) -> None:
        pass  # pragma: nocover

    @abstractmethod
    async def run(self) -> None:
        pass  # pragma: nocover
