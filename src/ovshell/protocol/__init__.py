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
)
from typing_extensions import Protocol
from abc import abstractmethod
from dataclasses import dataclass

import urwid

BasicType = Union[int, str, float]
JsonType = Union[BasicType, List[BasicType], Dict[str, BasicType]]

JT = TypeVar("JT", bound=JsonType)


class StoredSettings(Protocol):
    def setdefault(self, key: str, value: JsonType) -> None:
        pass

    def set(self, key: str, value: Optional[JsonType], save: bool = False):
        pass

    def get(self, key: str, type: Type[JT], default: JT = None) -> Optional[JT]:
        pass

    def save(self) -> None:
        pass


class SettingActivator(Protocol):
    @abstractmethod
    def open_value_popup(self, content: urwid.Widget) -> None:
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


class App(Protocol):
    name: str
    title: str
    description: str
    priority: int

    def launch(self) -> None:
        pass


class Activity(Protocol):
    @abstractmethod
    def create(self) -> urwid.Widget:
        pass

    def destroy(self) -> None:
        pass

    def activate(self) -> None:
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


class ScreenManager(Protocol):
    @abstractmethod
    def push_activity(self, activity: Activity) -> None:
        pass

    @abstractmethod
    def pop_activity(self) -> None:
        pass

    @abstractmethod
    def push_modal(self, activity: Activity, options: ModalOptions) -> None:
        pass


class OpenVarioOS(Protocol):
    @abstractmethod
    def mount_boot(self) -> None:
        pass

    @abstractmethod
    def unmount_boot(self) -> None:
        pass

    @abstractmethod
    def read_file(self, filename: str) -> bytes:
        pass

    @abstractmethod
    def write_file(self, filename: str, content: bytes) -> None:
        pass


class Extension(Protocol):
    id: str
    title: str

    def list_settings(self) -> Sequence[Setting]:
        return []

    def list_apps(self) -> Sequence[App]:
        return []


ExtensionFactory = Callable[[str, "OpenVarioShell"], Extension]


class ExtensionManager(Protocol):
    @abstractmethod
    def list_extensions(self) -> Iterable[Extension]:
        pass


class OpenVarioShell(Protocol):
    screen: ScreenManager
    settings: StoredSettings
    extensions: ExtensionManager
    os: OpenVarioOS

    @abstractmethod
    def quit(self) -> None:
        pass
