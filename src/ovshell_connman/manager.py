import asyncio
import types
import weakref
from typing import Any, Callable, Optional, Sequence, cast

from dbus_next import Variant
from dbus_next.errors import DBusError, InterfaceNotFoundError

from ovshell.api import AbstractMessageBus

from . import model
from .api import ConnmanManager, ConnmanNotAvailableException, ConnmanService
from .api import ConnmanState, ConnmanTechnology
from .dbusiface import ConnmanManagerProxyInterface, ConnmanServiceProxyInterface
from .dbusiface import ConnmanTechnologyProxyInterface


class ConnmanServiceProxy:
    _iface: Optional[ConnmanServiceProxyInterface]
    _change_handlers: list[weakref.WeakMethod]

    def __init__(self, svc: ConnmanService, bus: AbstractMessageBus) -> None:
        self.service = svc
        self._bus = bus
        self._iface = None
        self._change_handlers = []
        self._tracking = False
        self._tracking_lock = asyncio.Lock()

    async def connect(self) -> None:
        return await (await self._get_service_iface()).call_connect()

    async def remove(self) -> None:
        return await (await self._get_service_iface()).call_remove()

    async def disconnect(self) -> None:
        return await (await self._get_service_iface()).call_disconnect()

    async def start_tracking(self) -> None:
        async with self._tracking_lock:
            if self._tracking:
                return

            try:
                iface = await self._get_service_iface()
            except InterfaceNotFoundError:
                return
            iface.on_property_changed(self._on_property_changed)
            self._tracking = True

    def stop_tracking(self) -> None:
        if self._iface is None:
            return
        self._iface.off_property_changed(self._on_property_changed)

    def is_tracking(self) -> bool:
        return self._tracking

    def on_change(self, handler: Callable[[ConnmanService], None]) -> None:
        assert isinstance(handler, types.MethodType)
        self._change_handlers.append(weakref.WeakMethod(handler))

    def off_change(self, handler: Callable[[ConnmanService], None]) -> None:
        self._change_handlers = [wh for wh in self._change_handlers if wh() == handler]

    def _fire_changed(self) -> None:
        for wh in self._change_handlers:
            h = wh()
            if h is not None:
                h(self.service)

    def _on_property_changed(self, name: str, value: Variant) -> None:
        model.update_service_from_props(self.service, {name: value})
        self._fire_changed()

    async def _get_service_iface(self) -> ConnmanServiceProxyInterface:
        if self._iface is not None:
            return self._iface

        introspection = await self._bus.introspect("net.connman", self.service.path)
        proxy = self._bus.get_proxy_object(
            "net.connman", self.service.path, introspection
        )
        iface = proxy.get_interface("net.connman.Service")
        self._iface = cast(ConnmanServiceProxyInterface, iface)
        return self._iface


class ConnmanTechnologyProxy:
    def __init__(self, tech: ConnmanTechnology, bus: AbstractMessageBus) -> None:
        self._bus = bus
        self._tech = tech

    async def set_property(self, prop: str, value: Variant) -> None:
        iface = await self._get_tech_iface()
        return await iface.call_set_property(prop, value)

    async def scan(self) -> None:
        iface = await self._get_tech_iface()
        return await iface.call_scan()

    async def _get_tech_iface(self) -> ConnmanTechnologyProxyInterface:
        introspection = await self._bus.introspect("net.connman", self._tech.path)
        proxy = self._bus.get_proxy_object(
            "net.connman", self._tech.path, introspection
        )
        iface = proxy.get_interface("net.connman.Technology")
        return cast(ConnmanTechnologyProxyInterface, iface)


class ConnmanManagerImpl(ConnmanManager):
    technologies: list[ConnmanTechnology]
    _manager_props: dict[str, Variant]

    _tech_change_handlers: list[weakref.WeakMethod]
    _svc_change_handlers: list[weakref.WeakMethod]

    _svc_proxies: dict[str, ConnmanServiceProxy]
    _svc_order: list[str]

    def __init__(self, bus: AbstractMessageBus) -> None:
        self._bus = bus
        self.technologies = []
        self._manager_props = {}
        self._tech_change_handlers = []
        self._svc_change_handlers = []

        self._svc_proxies = {}
        self._svc_order = []

    async def setup(self) -> None:
        try:
            introspection = await self._bus.introspect("net.connman", "/")
            proxy = self._bus.get_proxy_object("net.connman", "/", introspection)
            self._manager_iface = cast(
                ConnmanManagerProxyInterface, proxy.get_interface("net.connman.Manager")
            )
        except DBusError as e:
            raise ConnmanNotAvailableException() from e

        self._subscribe_events(self._manager_iface)
        self._manager_props = await self._fetch_properties(self._manager_iface)
        await self._refresh_technologies()
        await self._refresh_services()

    def teardown(self) -> None:
        self._unsubscribe_events(self._manager_iface)
        for svcp in self._svc_proxies.values():
            svcp.stop_tracking()

    def list_services(self) -> Sequence[model.ConnmanService]:
        svcs = []
        for path in self._svc_order:
            sp = self._svc_proxies[path]
            svcs.append(sp.service)
        return svcs

    def on_service_property_changed(
        self, service: ConnmanService, handler: Callable[[model.ConnmanService], None]
    ) -> None:
        svcp = self._svc_proxies[service.path]
        svcp.on_change(handler)

    def off_service_property_changed(
        self, service: ConnmanService, handler: Callable[[ConnmanService], None]
    ) -> None:
        svcp = self._svc_proxies[service.path]
        svcp.off_change(handler)

    async def connect(self, service: ConnmanService) -> None:
        svcp = self._svc_proxies[service.path]
        await svcp.connect()
        await self._refresh_services()

    async def remove(self, service: ConnmanService) -> None:
        svcp = self._svc_proxies[service.path]
        await svcp.remove()
        await self._refresh_services()

    async def disconnect(self, service: ConnmanService) -> None:
        svcp = self._svc_proxies[service.path]
        await svcp.disconnect()
        await self._refresh_services()

    async def power(self, tech: ConnmanTechnology, on: bool) -> None:
        proxy = ConnmanTechnologyProxy(tech, self._bus)
        await proxy.set_property("Powered", Variant("b", on))
        await self._refresh_technologies()

    async def scan_all(self) -> int:
        ifaces = []
        for tech in self.technologies:
            if not tech.powered:
                continue
            if tech.type != "wifi":
                continue
            ifaces.append(ConnmanTechnologyProxy(tech, self._bus))
        if not ifaces:
            return 0

        scantasks = [asyncio.create_task(iface.scan()) for iface in ifaces]
        (done, pending) = await asyncio.wait(
            scantasks, return_when=asyncio.ALL_COMPLETED
        )
        return len([res.result for res in done])

    def get_state(self) -> ConnmanState:
        if "State" not in self._manager_props:
            return ConnmanState.UNKNOWN
        state = self._manager_props["State"]
        return ConnmanState(state.value)

    def on_technologies_changed(self, handler: Callable[[], None]) -> None:
        assert isinstance(handler, types.MethodType)
        self._tech_change_handlers.append(weakref.WeakMethod(handler))

    def on_services_changed(self, handler: Callable[[], None]) -> None:
        assert isinstance(handler, types.MethodType)
        self._svc_change_handlers.append(weakref.WeakMethod(handler))

    def _subscribe_events(self, iface: ConnmanManagerProxyInterface):
        iface.on_property_changed(self._notify_property_changed)
        iface.on_services_changed(self._notify_service_changed)
        iface.on_technology_added(self._notify_tech_added)
        iface.on_technology_removed(self._notify_tech_removed)

    def _unsubscribe_events(self, iface: ConnmanManagerProxyInterface):
        iface.off_property_changed(self._notify_property_changed)
        iface.off_services_changed(self._notify_service_changed)
        iface.off_technology_added(self._notify_tech_added)
        iface.off_technology_removed(self._notify_tech_removed)

    async def _refresh_technologies(self) -> None:
        self.technologies = await self._fetch_technologies(self._manager_iface)
        self._fire_tech_changed()

    async def _fetch_technologies(
        self, iface: ConnmanManagerProxyInterface
    ) -> list[ConnmanTechnology]:
        techs = await iface.call_get_technologies()
        res = []
        for path, tech in techs:
            res.append(model.create_technology_from_props(path, tech))

        return res

    async def _fetch_properties(
        self, iface: ConnmanManagerProxyInterface
    ) -> dict[str, Variant]:
        return await iface.call_get_properties()

    async def _refresh_services(self) -> None:
        svcs = await self._manager_iface.call_get_services()
        self._notify_service_changed(svcs, [])

    def _notify_property_changed(self, name: str, value: Variant) -> None:
        self._manager_props[name] = value

    def _notify_service_changed(
        self, changed: list[tuple[str, dict[str, Variant]]], removed: list[str]
    ) -> None:
        totrack = []
        # Update props
        for path, dbusprops in changed:
            svcp = self._svc_proxies.get(path)
            if svcp is None:
                if "Name" not in dbusprops or "Type" not in dbusprops:
                    # This is an update message, we cannot create a service
                    continue
                svc = model.create_service_from_props(path, dbusprops)
                svcp = ConnmanServiceProxy(svc, self._bus)
                self._svc_proxies[path] = svcp
            else:
                svc = svcp.service
                model.update_service_from_props(svc, dbusprops)
            if not svcp.is_tracking():
                totrack.append(path)

        self._svc_order = [path for path, _ in changed if path in self._svc_proxies]
        if totrack:
            asyncio.create_task(self._start_tracking_services(totrack))
        self._fire_svc_changed()

    async def _start_tracking_services(self, paths: list[str]) -> None:
        for path in paths:
            svcp = self._svc_proxies[path]
            await svcp.start_tracking()

    def _notify_tech_added(self, path: str, props: dict[str, Any]) -> None:
        tech = model.create_technology_from_props(path, props)
        self.technologies.append(tech)
        self._fire_tech_changed()

    def _notify_tech_removed(self, path: str) -> None:
        self.technologies = [t for t in self.technologies if t.path != path]
        self._fire_tech_changed()

    def _fire_tech_changed(self) -> None:
        for wh in self._tech_change_handlers:
            h = wh()
            if h is not None:
                h()

    def _fire_svc_changed(self) -> None:
        for wh in self._svc_change_handlers:
            h = wh()
            if h is not None:
                h()
