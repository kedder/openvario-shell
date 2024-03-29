"""Interfaces for Openvario extensions"""

import asyncio
import enum
from abc import abstractmethod
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Callable, Coroutine, Generator, Iterable, Iterator, Optional
from typing import Sequence, TypeVar, Union

import urwid
from typing_extensions import AsyncIterator, Protocol, runtime_checkable

UrwidText = Union[str, tuple[str, str], list[Union[str, tuple[str, str]]]]
BasicType = Union[int, str, float]
JsonType = Union[BasicType, list[BasicType], dict[str, BasicType]]

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

    def setdefault(self, key: str, value: JsonType) -> None:
        """Set the value if it wasn't set before"""

    def set(self, key: str, value: Optional[JsonType], save: bool = False):
        """Set the settings value.

        if save is True, also store the settings on disk.
        """

    def get(
        self, key: str, type: type[JT], default: Optional[JT] = None
    ) -> Optional[JT]:
        """Return the settings value for the key.

        If value wasn't set yet, or value in settings is of different type
        than requested by `type` argument, return `default` value.
        """

    def getstrict(self, key: str, type: type[JT]) -> JT:
        """Return value for the key.

        The value must be set and must be not None. Otherwise exception
        will be raised.
        """

    def save(self) -> None:
        """Store the settings on permanent storage.

        Must be called after changing any setting.
        """


class SettingActivator(Protocol):
    def open_value_popup(self, content: urwid.Widget, width: int, height: int) -> None:
        pass

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

    async def readline(self) -> bytes:
        """Read one line from the device

        Can raise `IOError`. In this case, device connection is considered
        broken and device is removed from the `DeviceManager`.
        """

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

    def register(self, device: Device) -> None:
        """Register new device.

        NMEA stream from this device will be available immediately in
        all open NMEA streams"""

    def enumerate(self) -> list[Device]:
        """Enumerate all registred devices."""

    @contextmanager
    def open_nmea(self) -> Generator[NMEAStream, None, None]:
        """Open new NMEA stream.

        Supposed to be used as a context manager with new NMEAStream object.
        NMEA messages from all the registered devices will be sent to this
        stream until context manager exits.
        """


class ProcessManager(Protocol):
    """Process Manager.

    Wrapper for running asyncio tasks. Keeps a list of active tasks and
    handles task failures.
    """

    def start(self, coro: Coroutine) -> asyncio.Task:
        """Start coroutine as asyncio task and register it with the manager."""


class App(Protocol):
    """Openvario Shell Application.

    Application represents a runnable item in "Applications" menu of openvario
    shell.

    `App` objects are created by extensions (see `Extension.list_apps()`) and
    can run either fully "native" urwid activities inside the shell, or simply
    run external programs that fully take over the screen.
    """

    name: str
    title: str
    description: str
    priority: int

    def install(self, appinfo: "AppInfo") -> None:
        """Install application

        This method is run on openvario shell startup when application is
        found in one of the extensions for the first time.
        """
        return

    def launch(self) -> None:
        """Start the application"""


class Activity(Protocol):
    """Single view of Application.

    Activity represent one urwid "view" of the application. Activites are
    organized in a stack by `Screen Manager` and pushed to that stack by
    the application (becoming active screen seen by the user) and removed from
    the stack when user presses "Escape" (a.k.a "Cancel" or "Back") button.

    Activity has several lifecycle methods allowing it to react to certain
    events outside of its direct control.
    """

    def create(self) -> urwid.Widget:
        """Create an urwid widget for this activity.

        The created urwid widget will take all the space reserved for the
        activity by openvario shell. Typical lifecycle of the activity:

        * activate() - called once
        * show() - may be called multiple times
        * hide() - may be called multiple times
        * destroy() - called once

        Typically it will be the full screen except top and bottom lines, but
        for modal activities it might be less, depending on modal options.
        """

    def activate(self) -> None:
        """Lifecycle method called when activity is activated for the first
        time.
        """
        return

    def destroy(self) -> None:
        """Lifecycle method called when activity is removed from the activity
        stack.
        """
        return

    def hide(self) -> None:
        """Lifecycle method called when activity is being replaced by another
        activity on top of the activity stack.

        This activity will not receive input until shown again.
        """
        return

    def show(self) -> None:
        """Lifecycle method called when activity is shown for the first time
        and every time it ends up on top of the activity stack (allowing user
        to interact with it).
        """
        return


@dataclass
class ModalOptions:
    """Options for modal activities.

    Specify the screen area and location of the modal activity.
    """

    align: str
    width: Union[str, int, tuple[str, int]]
    valign: str
    height: Union[str, int, tuple[str, int]]
    min_width: Optional[int] = None
    min_height: Optional[int] = None
    left: int = 0
    right: int = 0
    top: int = 0
    bottom: int = 0


class Dialog(Protocol):
    """Dialog with several (or no) buttons

    Dialogs are special kinds of modal activities that contain buttons
    at the bottom. Each button is associated with the handler function,
    that may return True to close the dialog or False to keep it visible.
    """

    def add_button(self, label: str, handler: Callable[[], bool]) -> None:
        """Add a button to the dialog.

        `handler` is a function that should return True to close the dialog,
        or False to leave it open.
        """

    def no_buttons(self) -> None:
        """Instructs to make dialog with no buttons

        This can be useful for certain kind of non-interactive dialogs that
        will close automatically, without explicit user input.
        """


class IndicatorLocation(enum.Enum):
    """Location of top bar indicator."""

    LEFT = "left"
    RIGHT = "right"


class ScreenManager(Protocol):
    """Screen Manager.

    Provides methods for managing activities. Separate UI screens, implemented
    by activities are organized in a stack. New activities are pushed on
    top of the stack, making previously active activities "obscured" by it. When
    user exits the top activity, previous activity is shown again and become
    interactive.

    Activities may spawn asynchronous tasks, that may run as long as activity
    is alive.
    """

    def draw(self) -> None:
        """Force screen redraw."""

    @contextmanager
    def suspended(self) -> Iterator[None]:
        """Context manager that suspends the screen management

        Useful to run shell apps that require full control over the screen.
        """

    def push_activity(
        self, activity: Activity, palette: Optional[list[tuple]] = None
    ) -> None:
        """Push new activity to the activity stack.

        Previous top activity will become hidden, and new activity is shown,
        until user exits it by using explict UI controls (if any), or by
        pressing "Excape" button.
        """

    def pop_activity(self) -> None:
        """Explitily destroy the current top activity.

        Previous activity will pop to the top of the stack and will be shown.
        """

    def push_modal(self, activity: Activity, options: ModalOptions) -> None:
        """Push new modal activity.

        Part of the previous' activity UI (that is not covered by area,
        specified in `options`) will still be visible, but not interactive
        """

    def push_dialog(self, title: str, content: urwid.Widget) -> Dialog:
        """Push special modal activity as a `Dialog`.

        Dialog contents may be any urwid widget, that will be displayed in
        a box with a title. By default the dialog will have one "Close" button
        that does nothing other than close the dialog. If `Dialog.add_button()`
        is called, the default button will be replaced with explicitly set one.
        More than one button can be added that way.
        """

    def set_indicator(
        self, iid: str, markup: UrwidText, location: IndicatorLocation, weight: int
    ) -> None:
        """Set new indicator (icon on the top bar).

        All indicators must have the unique `iid` string, that is used to change
        or remove the indicator. Indicator will be visible on screen until is
        replaced or removed.

        Indicators of the same location are ordered by `weight` value.
        """

    def remove_indicator(self, iid: str) -> None:
        """Remvoe indicator with given `iid`.

        Indicator will be effectively hidden.
        """

    def set_status(self, text: UrwidText) -> None:
        """Set status message."""

    def spawn_task(self, activity: Activity, coro: Coroutine) -> asyncio.Task:
        """Spawn a task for the activity.

        Started task may run as long as activity is alive. When activity is
        destroyed, all tasks started by that activity are automatically
        cancelled.

        If task fails, the error will be shown in the status bar.
        """


class OSProcess(Protocol):
    stdout: asyncio.streams.StreamReader
    stderr: asyncio.streams.StreamReader

    async def wait(self) -> int:
        """Wait for process to finish, return return code"""


class DBusNotAvailableException(Exception):
    pass


class AbstractMessageBusIntrospection(Protocol):
    pass


class AbstractMessageBusProxyObject(Protocol):
    def get_interface(self, name: str) -> Any:
        pass


class AbstractMessageBus(Protocol):
    async def introspect(
        self, bus_name: str, path: str, timeout: float = 30.0
    ) -> AbstractMessageBusIntrospection:
        pass

    def get_proxy_object(
        self, bus_name: str, path: str, introspection: Any
    ) -> AbstractMessageBusProxyObject:
        pass

    def export(self, path: str, agent: Any) -> None:
        pass


class OpenVarioOS(Protocol):
    """Operating system abstractions

    The purpose of these abstractions is to allow openvario shell to run under
    different environment than actual openvario hardware. The protocol can be
    implemented for simulated or testing environment.
    """

    def path(self, path: str) -> str:
        """Return absolute path

        In general, the path is returned intact, unless it starts with double
        forward slash (//). In that case the first slash is replaced with
        the path, specified by OVSHELL_ROOTFS environment variable.
        """

    async def run(self, command: str, args: list[str]) -> OSProcess:
        """Run a system command and return instance, representing a running process"""

    def sync(self) -> None:
        """Flush filesystem caches"""

    def shut_down(self) -> None:
        """Shut down the system"""

    def restart(self) -> None:
        """Perform a system reboot"""

    def spawn_shell(self) -> None:
        """Spawn a system shell"""

    async def get_system_bus(self) -> AbstractMessageBus:
        """Return system DBUS object

        May raise DBusNotAvailableError.
        """


class Extension(Protocol):
    """Openvario extension.

    Extensions provide apps and settings to openvario shell. Extensions are
    registered as python package entry point, under "ovshell.extensions" name.
    An entry point function must return Extension object.
    """

    id: str
    title: str

    def list_settings(self) -> Sequence[Setting]:
        """Return settings provided by extensions.

        Returned `Setting`s are added to "Settings" menu.
        """
        return []

    def list_apps(self) -> Sequence[App]:
        """Return apps, provided by extension

        Apps are available to user in "Applications" menu.
        """
        return []

    def start(self) -> None:
        """Hook called on startup when extension is loaded"""
        return


ExtensionFactory = Callable[[str, "OpenVarioShell"], Extension]


class ExtensionManager(Protocol):
    """Extension manager.

    Enumerates and manages installed extensions.
    """

    def list_extensions(self) -> Iterable[Extension]:
        """List all currently installed extensions."""


@dataclass
class AppInfo:
    """Application info

    Holds metadata for application.
    """

    id: str
    app: App
    extension: Extension
    pinned: bool


class AppManager(Protocol):
    """Application manager

    Holds registry of all applications.
    """

    def list_apps(self) -> Iterable[AppInfo]:
        """Return list of all available applications"""

    def get(self, appid: str) -> Optional[AppInfo]:
        """Retrun application by id, or None if application is not found"""

    def pin(self, app: AppInfo, persist: bool = False) -> None:
        """Pin application.

        Make application appear on the main menu.
        """

    def unpin(self, app: AppInfo, persist: bool = False) -> None:
        """Remove application from list of pinned ones"""


class OpenVarioShell(Protocol):
    """Services for Openvario shell"""

    screen: ScreenManager
    settings: StoredSettings
    extensions: ExtensionManager
    apps: AppManager
    os: OpenVarioOS
    devices: DeviceManager
    processes: ProcessManager
