from typing import List, Iterable, Tuple, Optional, TypeVar, Type, Dict
import os

from ovshell import protocol

JT = TypeVar("JT", bound=protocol.JsonType)


class AppManagerStub(protocol.AppManager):
    def __init__(self, log: List[str]) -> None:
        self._log = log


class ExtensionManagerStub(protocol.ExtensionManager):
    def __init__(self, log: List[str]) -> None:
        self._log = log

    def list_extensions(self) -> Iterable[protocol.Extension]:
        return []


class ScreenManagerStub(protocol.ScreenManager):
    _log: List[str]
    _activities: List[protocol.Activity]

    def __init__(self, log: List[str]) -> None:
        self._log = log
        self._activities = []

    def push_activity(
        self, activity: protocol.Activity, palette: Optional[List[Tuple]] = None
    ) -> None:
        self._activities.append(activity)

    def pop_activity(self) -> None:
        self._activities.pop()

    def push_modal(
        self, activity: protocol.Activity, options: protocol.ModalOptions
    ) -> None:
        self._activities.append(activity)

    def stub_top_activity(self) -> Optional[protocol.Activity]:
        if not self._activities:
            return None
        return self._activities[-1]


class StoredSettingsStub(protocol.StoredSettings):
    _settings: Dict[str, Optional[protocol.JsonType]]

    def __init__(self, log: List[str]) -> None:
        self._log = log
        self._settings = {}

    def setdefault(self, key: str, value: protocol.JsonType) -> None:
        self._settings.setdefault(key, value)

    def set(self, key: str, value: Optional[protocol.JsonType], save: bool = False):
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


class OpenVarioOSStub(protocol.OpenVarioOS):
    def __init__(self, log: List[str], rootfs: str) -> None:
        self._log = log
        self._rootfs = rootfs

    def mount_boot(self) -> None:
        self._log.append("OS: Mount /boot")

    def unmount_boot(self) -> None:
        self._log.append("OS: Unmount /boot")

    def path(self, path: str) -> str:
        assert path.startswith("/"), "Absolute path is required"
        if not path.startswith("//"):
            return path

        return os.path.join(self._rootfs, path[2:])

    def shut_down(self) -> None:
        self._log.append("OS: Shut down")

    def restart(self) -> None:
        self._log.append("OS: Restart")


class OpenVarioShellStub(protocol.OpenVarioShell):
    _log: List[str]

    def __init__(self, fsroot: str) -> None:
        self._log = []
        self.apps = AppManagerStub(self._log)
        self.extensions = ExtensionManagerStub(self._log)
        self.screen = ScreenManagerStub(self._log)
        self.settings = StoredSettingsStub(self._log)
        self.os = OpenVarioOSStub(self._log, fsroot)

        self._fsroot = fsroot

    def quit(self) -> None:
        self._log.append("Shell: Quit")

    def get_stub_log(self) -> List[str]:
        return self._log
