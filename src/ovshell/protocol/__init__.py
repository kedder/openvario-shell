from typing import Dict, List, Union, Optional, Callable
from typing_extensions import Protocol
from abc import abstractmethod

import urwid

BasicType = Union[int, str, float]
JsonType = Optional[Union[BasicType, List[BasicType], Dict[str, BasicType]]]


class Extension(Protocol):
    id: str
    title: str


ExtensionFactory = Callable[[str, "OpenVarioShell"], Extension]


class StoredSettings(Protocol):
    def setdefault(self, key: str, value: JsonType) -> None:
        pass

    def set(self, key: str, value: JsonType, save: bool = False):
        pass

    def get(self, key: str, default=None) -> Optional[JsonType]:
        pass

    def save(self) -> None:
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


class OpenVarioShell(Protocol):
    screen: ScreenManager
    settings: StoredSettings
