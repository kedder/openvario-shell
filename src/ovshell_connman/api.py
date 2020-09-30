from typing import List
from abc import abstractmethod
from typing_extensions import Protocol

from dataclasses import dataclass


@dataclass
class ConnmanTechnology:
    path: str
    name: str
    type: str
    connected: bool
    powered: bool
    tethering: bool


@dataclass
class ConnmanService:
    path: str
    auto_connect: bool
    favorite: bool
    name: str
    security: List[str]
    state: str
    strength: int
    type: str


class ConnmanManager(Protocol):
    @abstractmethod
    async def get_technologies(self) -> List[ConnmanTechnology]:
        pass

    @abstractmethod
    async def get_services(self) -> List[ConnmanService]:
        pass

    @abstractmethod
    async def connect(self, service: ConnmanService) -> None:
        pass

    @abstractmethod
    async def scan_all(self) -> None:
        pass
