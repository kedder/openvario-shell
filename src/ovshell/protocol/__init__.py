from typing import (
    Dict,
    List,
    Union,
    Optional,
    Callable,
    Sequence,
    Iterable,
    Tuple,
    TypeVar,
    Type,
    Coroutine,
    Generator,
)
import enum
from typing_extensions import Protocol, runtime_checkable
from abc import abstractmethod
from dataclasses import dataclass
from contextlib import contextmanager
import asyncio

import urwid

UrwidText = Union[str, Tuple[str, str], List[Union[str, Tuple[str, str]]]]
BasicType = Union[int, str, float]
JsonType = Union[BasicType, List[BasicType], Dict[str, BasicType]]

JT = TypeVar("JT", bound=JsonType)


class StoredSettings(Protocol):
    @abstractmethod
    def setdefault(self, key: str, value: JsonType) -> None:
        pass

    @abstractmethod
    def set(self, key: str, value: Optional[JsonType], save: bool = False):
        pass

    @abstractmethod
    def get(self, key: str, type: Type[JT], default: JT = None) -> Optional[JT]:
        pass

    @abstractmethod
    def getstrict(self, key: str, type: Type[JT]) -> JT:
        pass

    @abstractmethod
    def save(self) -> None:
        pass


class SettingActivator(Protocol):
    @abstractmethod
    def open_value_popup(self, content: urwid.Widget, width: int, height: int) -> None:
        pass

    @abstractmethod
    def close_value_popup(self) -> None:
        pass


class Setting(Protocol):
    title: str
    value_label: str
    priority: int

    def activate(self, activator: SettingActivator) -> None:
        pass


@runtime_checkable
class Device(Protocol):
    id: str
    name: str

    @abstractmethod
    async def readline(self) -> bytes:
        pass

    @abstractmethod
    def write(self, data: bytes) -> None:
        pass


class SerialDevice(Device):
    baudrate: int
    path: str


@dataclass
class NMEA:
    device_id: str
    raw_message: str
    datatype: str
    fields: Sequence[str]


class NMEAStream:
    @abstractmethod
    async def read(self) -> NMEA:
        pass

    @abstractmethod
    def __aiter__(self):
        pass

    @abstractmethod
    async def __anext__(self):
        pass


class DeviceManager(Protocol):
    @abstractmethod
    def register(self, device: Device) -> None:
        pass

    @abstractmethod
    def list(self) -> List[Device]:
        pass

    @abstractmethod
    @contextmanager
    def open_nmea(self) -> Generator[NMEAStream, None, None]:
        pass


class ProcessManager(Protocol):
    @abstractmethod
    def start(self, coro: Coroutine) -> asyncio.Task:
        pass


class App(Protocol):
    name: str
    title: str
    description: str
    priority: int

    def install(self, appinfo: "AppInfo") -> None:
        pass

    @abstractmethod
    def launch(self) -> None:
        pass


class Activity(Protocol):
    @abstractmethod
    def create(self) -> urwid.Widget:
        pass

    def activate(self) -> None:
        pass

    def destroy(self) -> None:
        pass

    def hide(self) -> None:
        pass

    def show(self) -> None:
        pass


@dataclass
class ModalOptions:
    align: str
    width: Union[str, int, Tuple[str, int]]
    valign: str
    height: Union[str, int, Tuple[str, int]]
    min_width: Optional[int] = None
    min_height: Optional[int] = None
    left: int = 0
    right: int = 0
    top: int = 0
    bottom: int = 0


class Dialog(Protocol):
    @abstractmethod
    def add_button(self, label: str, handler: Callable[[], bool]) -> None:
        pass


class IndicatorLocation(enum.Enum):
    LEFT = "left"
    RIGHT = "right"


class ScreenManager(Protocol):
    @abstractmethod
    def push_activity(
        self, activity: Activity, palette: Optional[List[Tuple]] = None
    ) -> None:
        pass

    @abstractmethod
    def pop_activity(self) -> None:
        pass

    @abstractmethod
    def push_modal(self, activity: Activity, options: ModalOptions) -> None:
        pass

    @abstractmethod
    def push_dialog(self, title: str, content: urwid.Widget) -> Dialog:
        pass

    @abstractmethod
    def set_indicator(
        self, iid: str, markup: UrwidText, location: IndicatorLocation, weight: int
    ) -> None:
        pass

    @abstractmethod
    def remove_indicator(self, iid: str) -> None:
        pass

    @abstractmethod
    def spawn_task(self, activity: Activity, coro: Coroutine) -> asyncio.Task:
        pass


class OpenVarioOS(Protocol):
    @abstractmethod
    def mount_boot(self) -> None:
        pass

    @abstractmethod
    def unmount_boot(self) -> None:
        pass

    @abstractmethod
    def path(self, path: str) -> str:
        pass

    @abstractmethod
    def shut_down(self) -> None:
        pass

    @abstractmethod
    def restart(self) -> None:
        pass


class Extension(Protocol):
    id: str
    title: str

    def list_settings(self) -> Sequence[Setting]:
        return []

    def list_apps(self) -> Sequence[App]:
        return []

    def start(self) -> None:
        pass


ExtensionFactory = Callable[[str, "OpenVarioShell"], Extension]


class ExtensionManager(Protocol):
    @abstractmethod
    def list_extensions(self) -> Iterable[Extension]:
        pass


@dataclass
class AppInfo:
    id: str
    app: App
    extension: Extension
    pinned: bool


class AppManager(Protocol):
    @abstractmethod
    def list(self) -> Iterable[AppInfo]:
        pass

    @abstractmethod
    def get(self, appid: str) -> Optional[AppInfo]:
        pass

    @abstractmethod
    def pin(self, app: AppInfo, persist: bool = False) -> None:
        pass

    @abstractmethod
    def unpin(self, app: AppInfo, persist: bool = False) -> None:
        pass


class OpenVarioShell(Protocol):
    screen: ScreenManager
    settings: StoredSettings
    extensions: ExtensionManager
    apps: AppManager
    os: OpenVarioOS
    devices: DeviceManager
    processes: ProcessManager

    @abstractmethod
    def quit(self) -> None:
        pass
