import asyncio
from typing import Callable, Dict, List, Optional, Sequence, Tuple

from dbus_next import Variant

from ovshell_connman.api import ConnmanManager, ConnmanService, ConnmanState
from ovshell_connman.api import ConnmanTechnology

BusProps = Dict[str, Variant]
BusObjList = List[Tuple[str, BusProps]]


class NetConnmanStub:
    __signals: Dict[str, List[Callable]]

    def __init__(self) -> None:
        self.__signals = {}

    def stub_get_signals(self):
        return self.__signals

    def _connect_signal(self, signal: str, handler: Callable) -> None:
        hl = self.__signals.setdefault(signal, [])
        hl.append(handler)

    def _disconnect_signal(self, signal: str, handler: Callable) -> None:
        hl = self.__signals.setdefault(signal, [])
        hl.remove(handler)
        if not hl:
            del self.__signals[signal]

    def _fire_signal(self, signal: str, *args, **kwargs) -> None:
        hl = self.__signals.get(signal, [])
        for h in hl:
            h(*args, **kwargs)


class NetConnmanManagerStub(NetConnmanStub):
    __technologies: BusObjList
    __services: Dict[str, Dict[str, Variant]]
    __properties: BusProps
    __registered_agent: Optional[str]

    def __init__(self) -> None:
        super().__init__()
        self.__technologies = []
        self.__services = {}
        self.__properties = {}
        self.__registered_agent = None

    async def call_get_properties(self) -> BusProps:
        return self.__properties

    async def call_get_technologies(self) -> BusObjList:
        return self.__technologies

    async def call_get_services(self) -> BusObjList:
        return [(path, props) for path, props in self.__services.items()]

    async def call_register_agent(self, path) -> None:
        self.__registered_agent = path

    def on_property_changed(self, handler: Callable) -> None:
        self._connect_signal("property_changed", handler)

    def on_services_changed(self, handler: Callable) -> None:
        self._connect_signal("services_changed", handler)

    def on_technology_added(self, handler: Callable) -> None:
        self._connect_signal("technology_added", handler)

    def on_technology_removed(self, handler: Callable) -> None:
        self._connect_signal("technology_removed", handler)

    def off_property_changed(self, handler: Callable) -> None:
        self._disconnect_signal("property_changed", handler)

    def off_services_changed(self, handler: Callable) -> None:
        self._disconnect_signal("services_changed", handler)

    def off_technology_added(self, handler: Callable) -> None:
        self._disconnect_signal("technology_added", handler)

    def off_technology_removed(self, handler: Callable) -> None:
        self._disconnect_signal("technology_removed", handler)

    def stub_set_technologies(self, techs: BusObjList) -> None:
        for path, tech in self.__technologies:
            self._fire_signal("technology_removed", path)

        self.__technologies = techs

        for path, tech in techs:
            self._fire_signal("technology_added", path, tech)

    def stub_update_services(self, updates: BusObjList, removes: List[str]) -> None:
        for path, props in updates:
            existing = self.__services.get(path, {})
            existing.update(props)
        for path in removes:
            del self.__services[path]
        self._fire_signal("services_changed", updates, removes)

    def stub_set_properties(self, properties: BusProps) -> None:
        self.__properties = properties
        for name, value in properties.items():
            self._fire_signal("property_changed", name, value)


class NetConnmanTechnologyStub(NetConnmanStub):
    scan_called: int = 0
    props_updated: List[Tuple[str, Variant]]

    def __init__(self) -> None:
        super().__init__()
        self.props_updated = []

    async def call_scan(self) -> None:
        self.scan_called += 1

    async def call_set_property(self, name: str, value: Variant) -> None:
        self.props_updated.append((name, value))


class NetConnmanServiceStub(NetConnmanStub):
    log: List[str]
    properties: BusProps

    def __init__(self) -> None:
        super().__init__()
        self.log = []
        self.properties = {}

    async def call_connect(self) -> None:
        self.log.append("Connect")

    async def call_remove(self) -> None:
        self.log.append("Remove")

    async def call_disconnect(self) -> None:
        self.log.append("Disconnect")

    async def call_get_properties(self) -> BusProps:
        return self.properties

    def on_property_changed(self, handler: Callable) -> None:
        self._connect_signal("property_changed", handler)

    def off_property_changed(self, handler: Callable) -> None:
        self._disconnect_signal("property_changed", handler)

    def stub_properties_changed(self, updates: BusProps) -> None:
        self.properties.update(updates)
        for name, value in updates.items():
            self._fire_signal("property_changed", name, value)


class ConnmanManagerStub(ConnmanManager):
    technologies: List[ConnmanTechnology]
    _services: List[ConnmanService]
    _tech_callbacks: List[Callable[[], None]]
    _svc_callbacks: List[Callable[[], None]]
    _svcprop_callbacks: List[Callable[[ConnmanService], None]]

    _scanning: Optional["asyncio.Future[int]"] = None
    _stub_log: List[str]
    _state = ConnmanState.UNKNOWN

    def __init__(self) -> None:
        self.technologies = []
        self._services = []
        self._tech_callbacks = []
        self._svc_callbacks = []
        self._svcprop_callbacks = []
        self._stub_log = []

    async def setup(self) -> None:
        pass

    def teardown(self) -> None:
        self._stub_log.append("Teardown")

    def list_services(self) -> Sequence[ConnmanService]:
        return self._services

    def on_service_property_changed(
        self, service: ConnmanService, handler: Callable[[ConnmanService], None]
    ) -> None:
        self._svcprop_callbacks.append(handler)

    def off_service_property_changed(
        self, service: ConnmanService, handler: Callable[[ConnmanService], None]
    ) -> None:
        self._svcprop_callbacks = [
            cb for cb in self._svcprop_callbacks if cb != handler
        ]

    async def connect(self, service: ConnmanService) -> None:
        self._stub_log.append(f"Connect to {service.path}")

    async def remove(self, service: ConnmanService) -> None:
        self._stub_log.append(f"Remove {service.path}")

    async def disconnect(self, service: ConnmanService) -> None:
        self._stub_log.append(f"Disconnect {service.path}")

    async def power(self, tech: ConnmanTechnology, on: bool) -> None:
        onstr = "on" if on else "off"
        self._stub_log.append(f"Power {tech.path} {onstr}")

    def on_technologies_changed(self, handler: Callable[[], None]) -> None:
        self._tech_callbacks.append(handler)

    def on_services_changed(self, handler: Callable[[], None]) -> None:
        self._svc_callbacks.append(handler)

    async def scan_all(self) -> int:
        self._stub_log.append("Scanning...")
        self._scanning = asyncio.Future()
        res = await self._scanning
        self._scanning = None
        self._stub_log.append("Scanning completed")
        return res

    def get_state(self) -> ConnmanState:
        return self._state

    def stub_add_technology(self, tech: ConnmanTechnology) -> None:
        self.technologies.append(tech)
        self._fire_techs_changed()

    def stub_add_service(self, service: ConnmanService) -> None:
        self._services.append(service)
        self._fire_svcs_changed()

    def stub_set_services(self, services: List[ConnmanService]) -> None:
        self._services = services
        self._fire_svcs_changed()

    def stub_service_prop_changed(self, svc: ConnmanService) -> None:
        self._fire_svcprob_changed(svc)

    def stub_scan_completed(self) -> None:
        assert self._scanning is not None
        self._scanning.set_result(1)

    def stub_get_log(self) -> Sequence[str]:
        return self._stub_log

    def _fire_techs_changed(self):
        for h in self._tech_callbacks:
            h()

    def _fire_svcs_changed(self):
        for h in self._svc_callbacks:
            h()

    def _fire_svcprob_changed(self, svc: ConnmanService):
        for h in self._svcprop_callbacks:
            h(svc)
