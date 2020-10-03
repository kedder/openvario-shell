from typing import Optional, List, Any, Dict, Tuple

from dbus_next import Variant
from dbus_next.message_bus import BaseMessageBus
from dbus_next.proxy_object import BaseProxyInterface

from .api import ConnmanManager, ConnmanService, ConnmanTechnology, ConnmanState
from .agent import ConnmanAgentImpl
from .agentiface import ConnmanAgentInterface


class ConnmanManagerImpl(ConnmanManager):
    technologies: List[ConnmanTechnology]
    services: List[ConnmanService]
    _manager_props: Dict[str, Variant]

    def __init__(self, bus: BaseMessageBus) -> None:
        self._bus = bus
        self.technologies = []
        self.services = []
        self._manager_props = {}

    async def setup(self) -> None:
        introspection = await self._bus.introspect("net.connman", "/")
        proxy = self._bus.get_proxy_object("net.connman", "/", introspection)
        iface = proxy.get_interface("net.connman.Manager")

        await self._register_agent(iface)
        self._subscribe_events(iface)
        self._manager_props = await self._fetch_properties(iface)
        self.technologies = await self._fetch_technologies(iface)
        self.services = await self._fetch_services(iface)

    async def get_service(self, path: str) -> Optional[ConnmanService]:
        filtered = [svc for svc in self.services if svc.path == path]
        if not filtered:
            return None
        assert len(filtered) == 1
        return filtered[0]

    async def connect(self, service: ConnmanService) -> None:
        introspection = await self._bus.introspect("net.connman", service.path)
        proxy = self._bus.get_proxy_object("net.connman", service.path, introspection)
        iface = proxy.get_interface("net.connman.Service")
        await iface.call_connect()

    async def scan_all(self) -> None:
        pass

    def get_state(self) -> ConnmanState:
        if "State" not in self._manager_props:
            return ConnmanState.UNKNOWN
        state = self._manager_props["State"]
        return ConnmanState(state.value)

    def _subscribe_events(self, iface: BaseProxyInterface):
        iface.on_property_changed(self._notify_property_changed)
        iface.on_services_changed(self._notify_servics_changed)
        iface.on_technology_added(self._notify_tech_added)
        iface.on_technology_removed(self._notify_tech_removed)

    async def _register_agent(self, iface: BaseProxyInterface) -> None:
        agent = ConnmanAgentImpl()
        agent_iface = ConnmanAgentInterface(self, agent)
        self._bus.export("/org/ovshell/connman", agent_iface)
        await iface.call_register_agent("/org/ovshell/connman")

    async def _fetch_technologies(
        self, iface: BaseProxyInterface
    ) -> List[ConnmanTechnology]:
        techs = await iface.call_get_technologies()
        res = []
        for path, tech in techs:
            props = self._convert_tech_props(tech)
            res.append(ConnmanTechnology(path, **props))

        return res

    async def _fetch_properties(self, iface: BaseProxyInterface) -> Dict[str, Variant]:
        return await iface.call_get_properties()

    def _convert_tech_props(self, props: Dict[str, Variant]) -> Dict[str, Any]:
        propmap = {
            "Name": "name",
            "Type": "type",
            "Connected": "connected",
            "Powered": "powered",
        }
        return {pp: props[dp].value for dp, pp in propmap.items() if dp in props}

    async def _fetch_services(self, iface: BaseProxyInterface) -> List[ConnmanService]:
        svcs = await iface.call_get_services()
        res = []
        for path, svc in svcs:
            props = self._convert_service_props(svc)
            res.append(ConnmanService(path, **props))
        return res

    def _convert_service_props(self, props: Dict[str, Variant]) -> Dict[str, Any]:
        propmap = {
            "AutoConnect": "auto_connect",
            "Favorite": "favorite",
            "Name": "name",
            "Security": "security",
            "State": "state",
            "Strength": "strength",
            "Type": "type",
        }
        return {pp: props[dp].value for dp, pp in propmap.items() if dp in props}

    def _notify_property_changed(self, name: str, value: Variant) -> None:
        self._manager_props[name] = value
        print("PROP CANGED", name, value)

    def _notify_servics_changed(
        self, changed: List[Tuple[str, Dict[str, Variant]]], removed: List[str]
    ):
        svcmap = {svc.path: svc for svc in self.services}

        # Update props
        for path, dbusprops in changed:
            svc = svcmap.get(path)
            props = self._convert_service_props(dbusprops)
            if svc is None:
                svc = ConnmanService(path, **props)
                svcmap[path] = svc
            else:
                svc.__dict__.update(props)

        # Change order. This will also remove any removed services
        self.services = [svcmap[path] for path, _ in changed]

        print("New svcs:", self.services)

    def _notify_tech_added(self, path: str, props: Dict[str, Any]) -> None:
        tech = ConnmanTechnology(path, **self._convert_tech_props(props))
        self.technologies.append(tech)
        print("Tech added", tech)

    def _notify_tech_removed(self, path: str) -> None:
        self.technologies = [t for t in self.technologies if t.path != path]
        print("Tech removed", path)
