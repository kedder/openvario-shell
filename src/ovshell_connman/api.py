from typing import List, Dict, Any, Optional
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
    async def get_service(self, path: str) -> Optional[ConnmanService]:
        pass

    @abstractmethod
    async def scan_all(self) -> None:
        pass


class ConnmanAgent(Protocol):
    """Interface for connman agent

    See https://git.kernel.org/pub/scm/network/connman/connman.git/tree/doc/agent-api.txt
    """

    @abstractmethod
    def report_error(self, service: ConnmanService, error: str) -> None:
        pass

    @abstractmethod
    async def request_input(
        self, service: ConnmanService, fields: Dict[str, Dict[str, str]]
    ) -> Dict[str, Any]:
        pass

    @abstractmethod
    def cancel(self) -> None:
        pass
