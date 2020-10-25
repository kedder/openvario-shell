from typing import Optional, List, Any, Dict, Tuple, Callable
import asyncio

from dbus_next import Variant
from dbus_next.message_bus import BaseMessageBus
from dbus_next.proxy_object import BaseProxyInterface

from .api import ConnmanManager, ConnmanService, ConnmanTechnology, ConnmanState
from . import model


class ConnmanManagerImpl(ConnmanManager):
    technologies: List[ConnmanTechnology]
    services: List[ConnmanService]
    _manager_props: Dict[str, Variant]

    _tech_change_handlers: List[Callable[[], None]]
    _svc_change_handlers: List[Callable[[], None]]

    def __init__(self, bus: BaseMessageBus) -> None:
        self._bus = bus
        self.technologies = []
        self.services = []
        self._manager_props = {}
        self._tech_change_handlers = []
        self._svc_change_handlers = []

    async def setup(self) -> None:
        introspection = await self._bus.introspect("net.connman", "/")
        proxy = self._bus.get_proxy_object("net.connman", "/", introspection)
        iface = proxy.get_interface("net.connman.Manager")

        self._subscribe_events(iface)
        self._manager_props = await self._fetch_properties(iface)
        self.technologies = await self._fetch_technologies(iface)
        self.services = await self._fetch_services(iface)

        self._fire_tech_changed()
        self._fire_svc_changed()

    async def connect(self, service: ConnmanService) -> None:
        introspection = await self._bus.introspect("net.connman", service.path)
        proxy = self._bus.get_proxy_object("net.connman", service.path, introspection)
        iface = proxy.get_interface("net.connman.Service")
        await iface.call_connect()

    async def remove(self, service: ConnmanService) -> None:
        introspection = await self._bus.introspect("net.connman", service.path)
        proxy = self._bus.get_proxy_object("net.connman", service.path, introspection)
        iface = proxy.get_interface("net.connman.Service")
        await iface.call_remove()

    async def disconnect(self, service: ConnmanService) -> None:
        introspection = await self._bus.introspect("net.connman", service.path)
        proxy = self._bus.get_proxy_object("net.connman", service.path, introspection)
        iface = proxy.get_interface("net.connman.Service")
        await iface.call_disconnect()

    async def scan_all(self) -> None:
        ifaces = []
        for tech in self.technologies:
            if tech.type != "wifi":
                continue
            introspection = await self._bus.introspect("net.connman", tech.path)
            proxy = self._bus.get_proxy_object("net.connman", tech.path, introspection)
            ifaces.append(proxy.get_interface("net.connman.Technology"))

        await asyncio.wait([iface.call_scan() for iface in ifaces])

    def get_state(self) -> ConnmanState:
        if "State" not in self._manager_props:
            return ConnmanState.UNKNOWN
        state = self._manager_props["State"]
        return ConnmanState(state.value)

    def on_technologies_changed(self, handler: Callable[[], None]) -> None:
        self._tech_change_handlers.append(handler)

    def on_services_changed(self, handler: Callable[[], None]) -> None:
        self._svc_change_handlers.append(handler)

    def _subscribe_events(self, iface: BaseProxyInterface):
        iface.on_property_changed(self._notify_property_changed)
        iface.on_services_changed(self._notify_servics_changed)
        iface.on_technology_added(self._notify_tech_added)
        iface.on_technology_removed(self._notify_tech_removed)

    async def _fetch_technologies(
        self, iface: BaseProxyInterface
    ) -> List[ConnmanTechnology]:
        techs = await iface.call_get_technologies()
        res = []
        for path, tech in techs:
            res.append(model.create_technology_from_props(path, tech))

        return res

    async def _fetch_properties(self, iface: BaseProxyInterface) -> Dict[str, Variant]:
        return await iface.call_get_properties()

    async def _fetch_services(self, iface: BaseProxyInterface) -> List[ConnmanService]:
        svcs = await iface.call_get_services()
        res = []
        for path, svc in svcs:
            res.append(model.create_service_from_props(path, svc))
        return res

    def _notify_property_changed(self, name: str, value: Variant) -> None:
        self._manager_props[name] = value

    def _notify_servics_changed(
        self, changed: List[Tuple[str, Dict[str, Variant]]], removed: List[str]
    ):
        svcmap = {svc.path: svc for svc in self.services}

        # Update props
        for path, dbusprops in changed:
            svc = svcmap.get(path)
            if svc is None:
                svc = model.create_service_from_props(path, dbusprops)
                svcmap[path] = svc
            else:
                model.update_service_from_props(svc, dbusprops)

        # Change order. This will also remove any removed services
        self.services = [svcmap[path] for path, _ in changed]
        self._fire_svc_changed()

    def _notify_tech_added(self, path: str, props: Dict[str, Any]) -> None:
        tech = model.create_technology_from_props(path, props)
        self.technologies.append(tech)
        self._fire_tech_changed()

    def _notify_tech_removed(self, path: str) -> None:
        self.technologies = [t for t in self.technologies if t.path != path]
        self._fire_tech_changed()

    def _fire_tech_changed(self) -> None:
        for h in self._tech_change_handlers:
            h()

    def _fire_svc_changed(self) -> None:
        for h in self._svc_change_handlers:
            h()
