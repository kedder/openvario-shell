import asyncio
import os
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Callable, Coroutine, Dict, Generator, Iterable, List, Optional
from typing import Tuple, Type, TypeVar

import urwid
from dbus_next.message_bus import BaseMessageBus

from ovshell import api

JT = TypeVar("JT", bound=api.JsonType)


class AppManagerStub(api.AppManager):
    _app_infos: List[api.AppInfo]

    def __init__(self, log: List[str]) -> None:
        self._log = log
        self._app_infos = []

    def list(self) -> Iterable[api.AppInfo]:
        return self._app_infos

    def get(self, appid: str) -> Optional[api.AppInfo]:
        appbyid = {ai.id: ai for ai in self._app_infos}
        return appbyid.get(appid)

    def pin(self, app: api.AppInfo, persist: bool = False) -> None:
        pass

    def unpin(self, app: api.AppInfo, persist: bool = False) -> None:
        pass

    def stub_add_app(
        self, id: str, app: api.App, ext: api.Extension, pinned: bool = False
    ) -> None:
        self._app_infos.append(api.AppInfo(id, app, ext, pinned))


class ExtensionManagerStub(api.ExtensionManager):
    def __init__(self, log: List[str]) -> None:
        self._log = log

    def list_extensions(self) -> Iterable[api.Extension]:
        return []


class DialogStub(api.Dialog):
    def __init__(self, title: str, content: urwid.Widget):
        self.title = title
        self.content = content
        self.buttons: Dict[str, Callable[[], bool]] = {}

    def add_button(self, label: str, handler: Callable[[], bool]) -> None:
        self.buttons[label] = handler

    def no_buttons(self) -> None:
        self.buttons = {}

    def stub_press_button(self, label: str):
        return self.buttons[label]()


@dataclass
class TopIndicatorStub:
    id: str
    markup: api.UrwidText
    location: api.IndicatorLocation
    weight: int


class ScreenManagerStub(api.ScreenManager):
    _log: List[str]
    _activities: List[api.Activity]
    _tasks: List[Tuple[api.Activity, asyncio.Task]]
    _dialog: Optional[DialogStub]
    _indicators: Dict[str, TopIndicatorStub]
    _status: Optional[api.UrwidText]

    def __init__(self, log: List[str]) -> None:
        self._log = log
        self._activities = []
        self._tasks = []
        self._dialog = None
        self._indicators = {}
        self._status = None

    def draw(self) -> None:
        self._log.append("Screen redrawn")

    def push_activity(
        self, activity: api.Activity, palette: Optional[List[Tuple]] = None
    ) -> None:
        self._activities.append(activity)

    def pop_activity(self) -> None:
        if self._dialog is not None:
            # If dialog is open, close it
            self._dialog = None
            return

        self._activities.pop()

    def push_modal(self, activity: api.Activity, options: api.ModalOptions) -> None:
        self._activities.append(activity)

    def push_dialog(self, title: str, content: urwid.Widget) -> api.Dialog:
        self._dialog = DialogStub(title, content)
        return self._dialog

    def set_indicator(
        self,
        iid: str,
        markup: api.UrwidText,
        location: api.IndicatorLocation,
        weight: int,
    ) -> None:
        self._indicators[iid] = TopIndicatorStub(iid, markup, location, weight)

    def remove_indicator(self, iid: str) -> None:
        if iid in self._indicators:
            del self._indicators[iid]
        pass

    def spawn_task(self, activity: api.Activity, coro: Coroutine) -> asyncio.Task:
        task = asyncio.create_task(coro)
        self._tasks.append((activity, task))
        task.add_done_callback(self._task_done)
        return task

    def set_status(self, text: api.UrwidText) -> None:
        self._status = text

    def _task_done(self, task: asyncio.Task) -> None:
        if task.cancelled():
            return
        exc = task.exception()
        if exc is not None:
            raise exc

    def stub_top_activity(self) -> Optional[api.Activity]:
        if not self._activities:
            return None
        return self._activities[-1]

    def stub_dialog(self) -> Optional[DialogStub]:
        return self._dialog

    def stub_cancel_tasks(self) -> None:
        for act, task in self._tasks:
            task.cancel()

    async def stub_wait_for_tasks(self, act: api.Activity) -> None:
        acttasks = [t for a, t in self._tasks if a is act]
        await asyncio.wait(acttasks)

    def stub_get_indicator(self, iid: str) -> Optional[TopIndicatorStub]:
        return self._indicators.get(iid)

    def stub_list_indicators(self) -> List[TopIndicatorStub]:
        return list(self._indicators.values())

    def stub_get_status(self) -> Optional[api.UrwidText]:
        return self._status


class StoredSettingsStub(api.StoredSettings):
    _settings: Dict[str, Optional[api.JsonType]]

    def __init__(self, log: List[str]) -> None:
        self._log = log
        self._settings = {}

    def setdefault(self, key: str, value: api.JsonType) -> None:
        self._settings.setdefault(key, value)

    def set(self, key: str, value: Optional[api.JsonType], save: bool = False):
        self._settings[key] = value

    def get(self, key: str, type: Type[JT], default: JT = None) -> Optional[JT]:
        v = self._settings.get(key, default)
        return v if isinstance(v, type) else None

    def getstrict(self, key: str, type: Type[JT]) -> JT:
        v = self.get(key, type)
        assert v is not None
        return v

    def save(self) -> None:
        pass


class OSPRocessStub(api.OSProcess):
    def __init__(
        self, returncode: int = 0, stdout: bytes = b"", stderr: bytes = b""
    ) -> None:
        self._returncode = returncode
        self.stdout = asyncio.streams.StreamReader()
        self.stdout.feed_data(stdout)
        self.stdout.feed_eof()
        self.stderr = asyncio.streams.StreamReader()
        self.stderr.feed_data(stderr)
        self.stderr.feed_eof()

    async def wait(self) -> int:
        await asyncio.sleep(0)
        return self._returncode


class MessageBusIntrospectionStub:
    def __init__(self, bus_name: str, path: str) -> None:
        self.bus_name = bus_name
        self.path = path


class MessageBusProxyObjectStub:
    def __init__(
        self,
        bus_name: str,
        path: str,
        introspection: MessageBusIntrospectionStub,
        impls: Dict[str, Any],
    ) -> None:
        self.__bus_name = bus_name
        self.__path = path
        self.__introspection = introspection
        self.__impls = impls

    def get_interface(self, name: str):
        return self.__impls[name]
        # return MessageBusProxyInterfaceStub(name, self.__impls[name])


class MessageBusStub:
    _impls: Dict[str, Dict[str, Any]]
    _exported: Dict[str, Any]

    def __init__(self) -> None:
        self._impls = {}
        self._exported = {}

    async def introspect(
        self, bus_name: str, path: str, timeout: float = 30.0
    ) -> MessageBusIntrospectionStub:
        return MessageBusIntrospectionStub(bus_name, path)

    def get_proxy_object(
        self, bus_name: str, path: str, introspection: MessageBusIntrospectionStub
    ) -> MessageBusProxyObjectStub:
        return MessageBusProxyObjectStub(
            bus_name, path, introspection, self._impls.get(path, {})
        )

    def export(self, path: str, agent: Any) -> None:
        self._exported[path] = agent

    def stub_register_interface(self, path: str, iface_name: str, impl: Any) -> None:
        ifaces = self._impls.setdefault(path, {})
        ifaces[iface_name] = impl

    def stub_get_exported(self) -> Dict[str, Any]:
        return self._exported


class OpenVarioOSStub(api.OpenVarioOS):
    _stub_run_returncode: int = 0
    _stub_run_stdout: bytes = b""
    _stub_run_stderr: bytes = b""
    _stub_bus: Optional[MessageBusStub] = None
    _stub_bus_connected: "asyncio.Future[MessageBusStub]"

    def __init__(self, log: List[str], rootfs: str) -> None:
        self._log = log
        self._rootfs = rootfs
        self._stub_bus_connected = asyncio.Future()

    def mount_boot(self) -> None:
        self._log.append("OS: Mount /boot")

    def unmount_boot(self) -> None:
        self._log.append("OS: Unmount /boot")

    def path(self, path: str) -> str:
        assert path.startswith("/"), "Absolute path is required"
        if not path.startswith("//"):
            return path

        return os.path.join(self._rootfs, path[2:])

    async def run(self, command: str, args: List[str]) -> api.OSProcess:
        self._log.append(f"OS: Running {command} {' '.join(args)}")
        return OSPRocessStub(
            self._stub_run_returncode, self._stub_run_stdout, self._stub_run_stderr
        )

    def sync(self) -> None:
        self._log.append("OS: Sync")

    def shut_down(self) -> None:
        self._log.append("OS: Shut down")

    def restart(self) -> None:
        self._log.append("OS: Restart")

    def stub_expect_run(
        self, result: int = 0, stdout: bytes = b"", stderr: bytes = b""
    ) -> None:
        self._stub_run_returncode = result
        self._stub_run_stdout = stdout
        self._stub_run_stderr = stderr

    async def get_system_bus(self) -> BaseMessageBus:
        return await self._stub_bus_connected

    def stub_connect_bus(self) -> MessageBusStub:
        self._stub_bus = MessageBusStub()
        self._stub_bus_connected.set_result(self._stub_bus)
        return self._stub_bus

    def stub_fail_bus(self) -> None:
        self._stub_bus_connected.set_exception(
            api.DBusNotAvailableException("Stub connection failed")
        )


class NMEAStreamStub(api.NMEAStream):
    def __init__(self, nmeas: List[api.NMEA]) -> None:
        self._nmeas = list(reversed(nmeas))

    async def read(self) -> api.NMEA:
        return self._nmeas.pop()

    def __aiter__(self):
        return self

    async def __anext__(self):
        return await self.read()


class DeviceManagerStub(api.DeviceManager):
    _devices: List[api.Device]
    _nmeas: List[api.NMEA]

    def __init__(self, log: List[str]) -> None:
        self._log = log
        self._devices = list()
        self._nmeas = list()

    def register(self, device: api.Device) -> None:
        self._devices.append(device)
        self._log.append(f"Registered device {device.id}")

    def list(self) -> List[api.Device]:
        return self._devices

    @contextmanager
    def open_nmea(self) -> Generator[api.NMEAStream, None, None]:
        yield NMEAStreamStub(self._nmeas)

    def stub_add_nmea(self, nmeas: List[api.NMEA]) -> None:
        self._nmeas.extend(nmeas)

    def stub_remove_device(self, devid: str) -> None:
        self._devices = [dev for dev in self._devices if dev.id != devid]


class ProcessManagerStub(api.ProcessManager):
    def __init__(self, log: List[str]) -> None:
        self._log = log

    def start(self, coro: Coroutine) -> asyncio.Task:
        return asyncio.create_task(coro)


class OpenVarioShellStub(api.OpenVarioShell):
    _log: List[str]

    def __init__(self, fsroot: str) -> None:
        self._log = []
        self.apps = AppManagerStub(self._log)
        self.extensions = ExtensionManagerStub(self._log)
        self.screen = ScreenManagerStub(self._log)
        self.settings = StoredSettingsStub(self._log)
        self.os = OpenVarioOSStub(self._log, fsroot)
        self.devices = DeviceManagerStub(self._log)
        self.processes = ProcessManagerStub(self._log)

        self._fsroot = fsroot

    def quit(self) -> None:
        self._log.append("Shell: Quit")

    def get_stub_log(self) -> List[str]:
        return self._log

    def stub_teardown(self) -> None:
        self.screen.stub_cancel_tasks()
