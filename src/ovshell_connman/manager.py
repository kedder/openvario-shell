from typing import Optional, List

from dbus_next.message_bus import BaseMessageBus
from dbus_next.proxy_object import BaseProxyInterface

from .api import ConnmanManager, ConnmanService, ConnmanTechnology
from .agent import ConnmanAgentImpl
from .agentiface import ConnmanAgentInterface


class ConnmanManagerImpl(ConnmanManager):
    _iface: Optional[BaseProxyInterface] = None

    def __init__(self, bus: BaseMessageBus) -> None:
        self._bus = bus

    async def _get_manager_iface(self) -> BaseProxyInterface:
        if self._iface is not None:
            return self._iface

        introspection = await self._bus.introspect("net.connman", "/")

        proxy = self._bus.get_proxy_object("net.connman", "/", introspection)
        iface = proxy.get_interface("net.connman.Manager")
        self._mgr_iface = iface
        return iface

    async def register_agent(self) -> None:
        agent = ConnmanAgentImpl()
        agent_iface = ConnmanAgentInterface(self, agent)
        self._bus.export("/org/ovshell/connman", agent_iface)

        mgr = await self._get_manager_iface()
        await mgr.call_register_agent("/org/ovshell/connman")

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

    async def get_service(self, path: str) -> Optional[ConnmanService]:
        svcs = await self.get_services()

        filtered = [svc for svc in svcs if svc.path == path]
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
