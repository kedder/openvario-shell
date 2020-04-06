from typing_extensions import Protocol
from abc import abstractmethod

import urwid


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
