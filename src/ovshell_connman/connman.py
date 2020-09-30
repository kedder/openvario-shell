from typing import Optional, List

from dbus_next.constants import BusType
from dbus_next.proxy_object import BaseProxyInterface
from dbus_next.aio import MessageBus

from .api import ConnmanManager, ConnmanService, ConnmanTechnology


class ConnmanManagerImpl(ConnmanManager):
    _iface: Optional[BaseProxyInterface] = None

    def __init__(self) -> None:
        pass

    async def _get_manager_iface(self) -> BaseProxyInterface:
        if self._iface is not None:
            return self._iface

        bus = await MessageBus(bus_type=BusType.SYSTEM).connect()
        introspection = await bus.introspect("net.connman", "/")
        proxy = bus.get_proxy_object("net.connman", "/", introspection)
        iface = proxy.get_interface("net.connman.Manager")
        self._iface = iface
        return iface

    async def get_technologies(self) -> List[ConnmanTechnology]:
        iface = await self._get_manager_iface()
        techs = await iface.call_get_technologies()
        res = []
        for path, tech in techs:
            res.append(
                ConnmanTechnology(
                    path=path,
                    name=tech["Name"].value,
                    type=tech["Type"].value,
                    connected=tech["Type"].value,
                    powered=tech["Powered"].value,
                    tethering=tech["Tethering"].value,
                )
            )

        return res

    async def get_services(self) -> List[ConnmanService]:
        iface = await self._get_manager_iface()
        svcs = await iface.call_get_services()
        res = []
        for path, svc in svcs:
            res.append(
                ConnmanService(
                    path=path,
                    auto_connect=svc["AutoConnect"].value,
                    favorite=svc["Favorite"].value,
                    name=svc["Name"].value,
                    security=svc["Security"].value,
                    state=svc["State"].value,
                    strength=svc["Strength"].value,
                    type=svc["Type"].value,
                )
            )
        return res
