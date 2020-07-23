"""Interfaces for Openvario extensions"""

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
from typing_extensions import Protocol, AsyncIterator, runtime_checkable
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
    """System setting storage

    Settings are simple key-value pairs. Key is a string, and value can be
    of any JSON-encodable type, including complex types, such as dictionaries
    and lists. Settings are (typically) stored in a JSON-encoded file in user
    config directory.

    After changing the setting, settings has to be persisted using `save()`
    method.
    """

    @abstractmethod
    def setdefault(self, key: str, value: JsonType) -> None:
        """Set the value if it wasn't set before"""

    @abstractmethod
    def set(self, key: str, value: Optional[JsonType], save: bool = False):
        """Set the settings value.

        if save is True, also store the settings on disk.
        """

    @abstractmethod
    def get(self, key: str, type: Type[JT], default: JT = None) -> Optional[JT]:
        """Return the settings value for the key.

        If value wasn't set yet, or value in settings is of different type
        than requested by `type` argument, return `default` value.
        """

    @abstractmethod
    def getstrict(self, key: str, type: Type[JT]) -> JT:
        """Return value for the key.

        The value must be set and must be not None. Otherwise exception
        will be raised.
        """

    @abstractmethod
    def save(self) -> None:
        """Store the settings on permanent storage.

        Must be called after changing any setting.
        """


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
    """External device

    Represents a driver for externally connected device. Device can send and
    receive data from Openvario.

    Openvario extensions are responsible for creating instances of Devices and
    registering them with `DeviceManager`.
    """

    id: str
    name: str

    @abstractmethod
    async def readline(self) -> bytes:
        """Read one line from the device

        Can raise `IOError`. In this case, device connection is considered
        broken and device is removed from the `DeviceManager`.
        """

    @abstractmethod
    def write(self, data: bytes) -> None:
        """Write data to the device

        Can raise `IOError`. In this case, device connection is considered
        broken and device is removed from the `DeviceManager`.
        """


class SerialDevice(Device):
    """Serial device.

    Device extension for serial devices, that are communicating on some
    particular baud rate.
    """

    baudrate: int
    path: str


@dataclass
class NMEA:
    """Parsed NMEA message

    Each NMEA message are associated with the device that produced it.
    """

    device_id: str
    raw_message: str
    datatype: str
    fields: Sequence[str]


class NMEAStream:
    """The stream of NMEA messages

    Asynchronously provides an infinite iterator for NMEA messages, produced
    across all connected devices. This object can be obtained with
    `DeviceManager.open_nmea()`.
    """

    @abstractmethod
    async def read(self) -> NMEA:
        """Read next NMEA message"""

    @abstractmethod
    def __aiter__(self) -> AsyncIterator[NMEA]:
        """Return (infinite) iterator for NMEA messages"""

    @abstractmethod
    async def __anext__(self) -> NMEA:
        """Return next NMEA message (when available)"""


class DeviceManager(Protocol):
    """Device manager

    Maintains a registry of active devices and dispatches NMEA streams
    to clients.
    """

    @abstractmethod
    def register(self, device: Device) -> None:
        """Register new device.

        NMEA stream from this device will be available immediately in
        all open NMEA streams"""

    @abstractmethod
    def list(self) -> List[Device]:
        """Enumerate all registred devices"""

    @abstractmethod
    @contextmanager
    def open_nmea(self) -> Generator[NMEAStream, None, None]:
        """Open new NMEA stream

        Supposed to be used as a context manager with new NMEAStream object.
        NMEA messages from all the registered devices will be sent to this
        stream until context manager exits.
        """


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

    @abstractmethod
    def no_buttons(self) -> None:
        pass


class IndicatorLocation(enum.Enum):
    LEFT = "left"
    RIGHT = "right"


class ScreenManager(Protocol):
    @abstractmethod
    def draw(self) -> None:
        pass

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
    def sync(self) -> None:
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
