import asyncio
from collections import Counter
from typing import Callable
from typing import Counter as TCounter
from typing import Dict, List, Tuple

import pytest
from dbus_next import Variant

from ovshell import testing
from ovshell_connman.api import ConnmanService, ConnmanServiceState
from ovshell_connman.manager import ConnmanManagerImpl

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

    def __init__(self) -> None:
        super().__init__()
        self.__technologies = []
        self.__services = {}
        self.__properties = {}

    async def call_get_properties(self) -> BusProps:
        return self.__properties

    async def call_get_technologies(self) -> BusObjList:
        return self.__technologies

    async def call_get_services(self) -> BusObjList:
        return [(path, props) for path, props in self.__services.items()]

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

    def __init__(self) -> None:
        super().__init__()
        self.log = []

    async def call_connect(self) -> None:
        self.log.append("Connect")

    async def call_remove(self) -> None:
        self.log.append("Remove")

    async def call_disconnect(self) -> None:
        self.log.append("Disconnect")

    def on_property_changed(self, handler: Callable) -> None:
        self._connect_signal("property_changed", handler)

    def off_property_changed(self, handler: Callable) -> None:
        self._disconnect_signal("property_changed", handler)

    def stub_properties_changed(self, updates: BusProps) -> None:
        for name, value in updates.items():
            self._fire_signal("property_changed", name, value)


class TestConnmanManagerImpl:
    @pytest.fixture(autouse=True)
    def setup(self, ovshell: testing.OpenVarioShellStub) -> None:
        self.ovshell = ovshell
        self.bus = ovshell.os.stub_connect_bus()
        self.net_connman_manager = NetConnmanManagerStub()
        self.bus.stub_register_interface(
            "/", "net.connman.Manager", self.net_connman_manager
        )

        self.sample_service_props = {
            "AutoConnect": Variant("b", False),
            "Favorite": Variant("b", False),
            "Name": Variant("s", "Skynet"),
            "Security": Variant("s", "wpa"),
            "Strength": Variant("i", 78),
            "Type": Variant("s", "wifi"),
            "State": Variant("s", "idle"),
        }

    @pytest.mark.asyncio
    async def test_setup(self, ovshell: testing.OpenVarioShellStub) -> None:
        # GIVEN
        mgr = ConnmanManagerImpl(await ovshell.os.get_system_bus())

        # WHEN
        await mgr.setup()
        assert len(mgr.technologies) == 0

        self.net_connman_manager.stub_set_technologies(
            [
                (
                    "/path1",
                    {
                        "Name": Variant("s", "One"),
                        "Type": Variant("s", "wifi"),
                        "Connected": Variant("b", False),
                        "Powered": Variant("b", False),
                    },
                )
            ]
        )

        # THEN
        assert len(mgr.technologies) == 1

    @pytest.mark.asyncio
    async def test_teardown(self, ovshell: testing.OpenVarioShellStub) -> None:
        # GIVEN
        mgr = ConnmanManagerImpl(await ovshell.os.get_system_bus())
        svc1_iface = NetConnmanServiceStub()
        self.bus.stub_register_interface("/svc1", "net.connman.Service", svc1_iface)
        await mgr.setup()
        self.net_connman_manager.stub_update_services(
            [("/svc1", self.sample_service_props,)], [],
        )
        await asyncio.sleep(0)

        signals = self.net_connman_manager.stub_get_signals()
        assert signals.keys() == {
            "property_changed",
            "services_changed",
            "technology_added",
            "technology_removed",
        }

        assert svc1_iface.stub_get_signals().keys() == {"property_changed"}

        # WHEN
        mgr.teardown()

        # THEN
        signals = self.net_connman_manager.stub_get_signals()
        assert signals == {}
        assert svc1_iface.stub_get_signals() == {}

    @pytest.mark.asyncio
    async def test_scan_all(self) -> None:
        # GIVEN
        self.net_connman_manager.stub_set_technologies(
            [
                (
                    "/eth",
                    {
                        "Name": Variant("s", "Ethernet"),
                        "Type": Variant("s", "ethernet"),
                        "Connected": Variant("b", False),
                        "Powered": Variant("b", False),
                    },
                ),
                (
                    "/wifi",
                    {
                        "Name": Variant("s", "Wifi"),
                        "Type": Variant("s", "wifi"),
                        "Connected": Variant("b", False),
                        "Powered": Variant("b", False),
                    },
                ),
            ]
        )

        net_connman_tech = NetConnmanTechnologyStub()
        self.bus.stub_register_interface(
            "/wifi", "net.connman.Technology", net_connman_tech
        )
        mgr = ConnmanManagerImpl(self.bus)
        await mgr.setup()

        # WHEN
        assert len(mgr.technologies) > 0
        scanned = await mgr.scan_all()

        # THEN
        assert scanned == 1  # only wifi is scanned
        assert net_connman_tech.scan_called == 1

    @pytest.mark.asyncio
    async def test_tech_power(self) -> None:
        # GIVEN
        self.net_connman_manager.stub_set_technologies(
            [
                (
                    "/eth",
                    {
                        "Name": Variant("s", "Ethernet"),
                        "Type": Variant("s", "ethernet"),
                        "Connected": Variant("b", False),
                        "Powered": Variant("b", False),
                    },
                ),
            ]
        )
        net_connman_tech = NetConnmanTechnologyStub()
        self.bus.stub_register_interface(
            "/eth", "net.connman.Technology", net_connman_tech
        )
        mgr = ConnmanManagerImpl(self.bus)
        await mgr.setup()
        await asyncio.sleep(0)

        # WHEN
        techs = mgr.technologies
        assert len(techs) == 1
        tech_eth = techs[0]
        await mgr.power(tech_eth, on=True)

        # THEN
        assert net_connman_tech.props_updated == [("Powered", Variant("b", True))]

    @pytest.mark.asyncio
    async def test_services_changed(self) -> None:
        # GIVEN
        mgr = ConnmanManagerImpl(self.bus)
        svc1_iface = NetConnmanServiceStub()
        self.bus.stub_register_interface("/svc1", "net.connman.Service", svc1_iface)
        await mgr.setup()

        self.net_connman_manager.stub_update_services(
            [("/svc1", self.sample_service_props,)], [],
        )
        await asyncio.sleep(0)

        # WHEN
        svcs = mgr.list_services()

        # THEN
        assert len(svcs) == 1
        svc1 = svcs[0]
        assert svc1.path == "/svc1"
        assert svc1.name == "Skynet"
        assert svc1.state == ConnmanServiceState.IDLE

        # Manager should be subscribed to service updates now
        signals = svc1_iface.stub_get_signals()
        assert signals.keys() == {"property_changed"}

        # WHEN
        self.net_connman_manager.stub_update_services(
            [("/svc1", {"State": Variant("s", "online")})], [],
        )

        # THEN
        svcs = mgr.list_services()
        assert len(svcs) == 1
        svc1 = svcs[0]
        assert svc1.path == "/svc1"
        assert svc1.name == "Skynet"
        assert svc1.state == ConnmanServiceState.ONLINE

    @pytest.mark.asyncio
    async def test_track_service_props(self) -> None:
        # GIVEN
        mgr = ConnmanManagerImpl(self.bus)
        svc1_iface = NetConnmanServiceStub()
        self.bus.stub_register_interface("/svc1", "net.connman.Service", svc1_iface)
        await mgr.setup()

        self.net_connman_manager.stub_update_services(
            [("/svc1", self.sample_service_props,)], [],
        )
        await asyncio.sleep(0)

        svcs = mgr.list_services()
        assert len(svcs) == 1

        # WHEN
        svc1_iface.stub_properties_changed(
            {"Strength": Variant("i", 56), "State": Variant("s", "online")}
        )

        # THEN
        svcs = mgr.list_services()
        assert len(svcs) == 1
        svc1 = svcs[0]
        assert svc1.path == "/svc1"
        assert svc1.name == "Skynet"
        assert svc1.state == ConnmanServiceState.ONLINE
        assert svc1.strength == 56

    @pytest.mark.asyncio
    async def test_on_service_prop_changed(self) -> None:
        # GIVEN
        mgr = ConnmanManagerImpl(self.bus)
        svc1_iface = NetConnmanServiceStub()
        self.bus.stub_register_interface("/svc1", "net.connman.Service", svc1_iface)
        await mgr.setup()

        self.net_connman_manager.stub_update_services(
            [("/svc1", self.sample_service_props,)], [],
        )
        await asyncio.sleep(0)

        class ServiceListener:
            def __init__(self, counter) -> None:
                self.counter = counter

            def prop_changed(self, svc: ConnmanService) -> None:
                self.counter.update(["changed"])

        cnt: TCounter[str] = Counter()
        listener = ServiceListener(cnt)

        svcs = mgr.list_services()
        assert len(svcs) == 1
        svc1 = svcs[0]
        mgr.on_service_property_changed(svc1, listener.prop_changed)

        # WHEN
        svc1_iface.stub_properties_changed(
            {"Strength": Variant("i", 56), "State": Variant("s", "online")}
        )

        # THEN
        # 2 properties have changed
        assert cnt["changed"] == 2

        # WHEN
        # After listener is deleted, counter should not change (we should
        # not keep references to the listener and allow it to be destroyed)
        del listener
        svc1_iface.stub_properties_changed({"Strength": Variant("i", 32)})

        # THEN
        # Changes are not registered anymore
        assert cnt["changed"] == 2

    @pytest.mark.asyncio
    async def test_svc_connect(self) -> None:
        mgr = ConnmanManagerImpl(self.bus)
        svc1_iface = NetConnmanServiceStub()
        self.bus.stub_register_interface("/svc1", "net.connman.Service", svc1_iface)
        await mgr.setup()

        self.net_connman_manager.stub_update_services(
            [("/svc1", self.sample_service_props,)], [],
        )
        await asyncio.sleep(0)

        svcs = mgr.list_services()
        assert len(svcs) == 1
        svc1 = svcs[0]

        # WHEN
        await mgr.connect(svc1)

        # THEN
        assert svc1_iface.log == ["Connect"]

    @pytest.mark.asyncio
    async def test_svc_remove(self) -> None:
        mgr = ConnmanManagerImpl(self.bus)
        svc1_iface = NetConnmanServiceStub()
        self.bus.stub_register_interface("/svc1", "net.connman.Service", svc1_iface)
        await mgr.setup()

        self.net_connman_manager.stub_update_services(
            [("/svc1", self.sample_service_props,)], [],
        )
        await asyncio.sleep(0)

        svcs = mgr.list_services()
        assert len(svcs) == 1
        svc1 = svcs[0]

        # WHEN
        await mgr.remove(svc1)

        # THEN
        assert svc1_iface.log == ["Remove"]

    @pytest.mark.asyncio
    async def test_svc_disconnect(self) -> None:
        mgr = ConnmanManagerImpl(self.bus)
        svc1_iface = NetConnmanServiceStub()
        self.bus.stub_register_interface("/svc1", "net.connman.Service", svc1_iface)
        await mgr.setup()

        self.net_connman_manager.stub_update_services(
            [("/svc1", self.sample_service_props,)], [],
        )
        await asyncio.sleep(0)

        svcs = mgr.list_services()
        assert len(svcs) == 1
        svc1 = svcs[0]

        # WHEN
        await mgr.disconnect(svc1)

        # THEN
        assert svc1_iface.log == ["Disconnect"]
