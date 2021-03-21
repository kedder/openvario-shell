import enum
from abc import abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Sequence

from typing_extensions import Protocol


class ConnmanState(enum.Enum):
    UNKNOWN = "unknown"
    OFFLINE = "offline"
    IDLE = "idle"
    READY = "ready"
    ONLINE = "online"


class ConnmanServiceState(enum.Enum):
    IDLE = "idle"
    FAILURE = "failure"
    ASSOCIATION = "association"
    CONFIGURATION = "configuration"
    READY = "ready"
    DISCONNECT = "disconnect"
    ONLINE = "online"


@dataclass
class ConnmanTechnology:
    path: str
    name: str
    type: str
    connected: bool
    powered: bool


@dataclass
class ConnmanService:
    path: str
    type: str
    name: str
    auto_connect: bool = False
    favorite: bool = False
    security: List[str] = field(default_factory=list)
    state: ConnmanServiceState = ConnmanServiceState.IDLE
    strength: int = 0


class ConnmanManager(Protocol):
    technologies: Sequence[ConnmanTechnology]

    @abstractmethod
    async def setup(self) -> None:
        """Subscripe to signals in order to keep track of services and technologies"""

    @abstractmethod
    def teardown(self) -> None:
        """Unsubscribe from events from setup

        Call this after manager is no longer used"""

    @abstractmethod
    def list_services(self) -> Sequence[ConnmanService]:
        """Return list of managed services"""

    @abstractmethod
    def on_service_property_changed(
        self, service: ConnmanService, handler: Callable[[ConnmanService], None]
    ) -> None:
        """Call handler when property of a given service changes"""

    @abstractmethod
    def off_service_property_changed(
        self, service: ConnmanService, handler: Callable[[ConnmanService], None]
    ) -> None:
        """Stop calling method on service property change"""

    @abstractmethod
    async def connect(self, service: ConnmanService) -> None:
        """Connect to given service"""

    @abstractmethod
    async def remove(self, service: ConnmanService) -> None:
        """Remove given service from favorites"""

    @abstractmethod
    async def disconnect(self, service: ConnmanService) -> None:
        """Disconnect from given service"""

    @abstractmethod
    async def power(self, tech: ConnmanTechnology, on: bool) -> None:
        """Turn the power of given technology on or off"""

    @abstractmethod
    def on_technologies_changed(self, handler: Callable[[], None]) -> None:
        """Call given method when technologies change"""

    @abstractmethod
    def on_services_changed(self, handler: Callable[[], None]) -> None:
        """Call given method when service change"""

    @abstractmethod
    async def scan_all(self) -> int:
        """Scan all technologies (that support scanning)

        Return the number of techs scanned.
        """

    @abstractmethod
    def get_state(self) -> ConnmanState:
        """Return current state of the connman"""


class Canceled(Exception):
    """Operation was cancelled"""


class ConnmanAgent(Protocol):
    """Interface for connman agent

    See https://git.kernel.org/pub/scm/network/connman/connman.git/tree/doc/agent-api.txt
    """

    @abstractmethod
    def report_error(self, service: ConnmanService, error: str) -> None:
        """Display error message to the user"""

    @abstractmethod
    async def request_input(
        self, service: ConnmanService, fields: Dict[str, Dict[str, str]]
    ) -> Dict[str, Any]:
        """Request input from the user"""

    @abstractmethod
    def cancel(self) -> None:
        """Inform that operation was canceled"""
