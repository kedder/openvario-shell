from typing import Dict, List, Union, Optional, Callable, Sequence, Iterable
from typing_extensions import Protocol
from abc import abstractmethod

import urwid

BasicType = Union[int, str, float]
JsonType = Optional[Union[BasicType, List[BasicType], Dict[str, BasicType]]]


class StoredSettings(Protocol):
    def setdefault(self, key: str, value: JsonType) -> None:
        pass

    def set(self, key: str, value: JsonType, save: bool = False):
        pass

    def get(self, key: str, default=None) -> Optional[JsonType]:
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


class Activity(Protocol):
    @abstractmethod
    def create(self) -> urwid.Widget:
        pass

    def destroy(self) -> None:
        pass

    def activate(self) -> None:
        pass


class ScreenManager(Protocol):
    @abstractmethod
    def push_activity(self, activity: Activity) -> None:
        pass

    @abstractmethod
    def pop_activity(self) -> None:
        pass


class Extension(Protocol):
    id: str
    title: str

    @abstractmethod
    def list_settings(self) -> Sequence[Setting]:
        pass


ExtensionFactory = Callable[[str, "OpenVarioShell"], Extension]


class ExtensionManager(Protocol):
    @abstractmethod
    def list_extensions(self) -> Iterable[Extension]:
        pass


class OpenVarioShell(Protocol):
    screen: ScreenManager
    settings: StoredSettings
    extensions: ExtensionManager
