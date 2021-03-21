import asyncio
from collections import Counter
from typing import Counter as TCounter

import pytest
from dbus_next import Variant

from ovshell import testing
from ovshell_connman.api import ConnmanService, ConnmanServiceState, ConnmanState
from ovshell_connman.manager import ConnmanManagerImpl

from .stubs import NetConnmanManagerStub, NetConnmanServiceStub
from .stubs import NetConnmanTechnologyStub


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

        self.sample_tech_props = {
            "Name": Variant("s", "Ethernet"),
            "Type": Variant("s", "ethernet"),
            "Connected": Variant("b", False),
            "Powered": Variant("b", False),
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
                ("/eth", self.sample_tech_props),
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
            [("/eth", self.sample_tech_props)]
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
    async def test_services_changed_incomplete_data(self) -> None:
        # GIVEN
        mgr = ConnmanManagerImpl(self.bus)
        svc1_iface = NetConnmanServiceStub()
        self.bus.stub_register_interface("/svc1", "net.connman.Service", svc1_iface)
        await mgr.setup()

        incomplete_props = {
            "Name": Variant("s", "Skynet"),
            "Type": Variant("s", "ethernet"),
        }
        self.net_connman_manager.stub_update_services(
            [("/svc1", incomplete_props,)], [],
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

    @pytest.mark.asyncio
    async def test_subscribers(self) -> None:
        # GIVEN

        class EventListener:
            def __init__(self, counter) -> None:
                self.counter = counter

            def techs_changed(self) -> None:
                self.counter.update(["tech changed"])

            def services_changed(self) -> None:
                self.counter.update(["services changed"])

        cnt: TCounter[str] = Counter()
        listener = EventListener(cnt)

        mgr = ConnmanManagerImpl(self.bus)
        svc1_iface = NetConnmanServiceStub()
        self.bus.stub_register_interface("/svc1", "net.connman.Service", svc1_iface)
        await mgr.setup()
        await asyncio.sleep(0)

        # WHEN
        mgr.on_services_changed(listener.services_changed)
        mgr.on_technologies_changed(listener.techs_changed)

        # Add tech
        self.net_connman_manager.stub_set_technologies(
            [("/eth0", self.sample_tech_props)]
        )
        # Remove and add another tech
        self.net_connman_manager.stub_set_technologies(
            [("/eth1", self.sample_tech_props)]
        )
        self.net_connman_manager.stub_update_services(
            [("/svc1", self.sample_service_props)], []
        )

        # THEN
        assert cnt["tech changed"] == 3  # 1 removed, 2 added
        assert cnt["services changed"] == 1

    @pytest.mark.asyncio
    async def test_get_state(self) -> None:
        # GIVEN
        mgr = ConnmanManagerImpl(self.bus)
        await mgr.setup()
        await asyncio.sleep(0)

        # WHEN
        state = mgr.get_state()

        # THEN
        assert state == ConnmanState.UNKNOWN

        # WHEN
        self.net_connman_manager.stub_set_properties({"State": Variant("s", "online")})
        state = mgr.get_state()

        # THEN
        assert state == ConnmanState.ONLINE
