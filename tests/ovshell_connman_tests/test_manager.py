from typing import Dict, List, Tuple

import pytest
from dbus_next import Variant

from ovshell import testing
from ovshell_connman.manager import ConnmanManagerImpl

BusProps = Dict[str, Variant]
BusObjList = List[Tuple[str, BusProps]]


class NetConnmanManagerStub:
    __technologies: BusObjList
    __services: BusObjList
    __properties: BusProps

    def __init__(self) -> None:
        self.__technologies = []
        self.__services = []
        self.__properties = {}

    async def get_properties(self) -> BusProps:
        return self.__properties

    async def get_technologies(self) -> BusObjList:
        return self.__technologies

    async def get_services(self) -> BusObjList:
        return self.__services

    def stub_set_technologies(self, techs: BusObjList) -> None:
        self.__technologies = techs

    def stub_set_services(self, services: BusObjList) -> None:
        self.__services = services

    def stub_set_properties(self, properties: BusProps) -> None:
        self.__properties = properties


class NetConnmanTechnologyStub:
    scan_called: int = 0

    def __init__(self) -> None:
        pass

    async def scan(self) -> None:
        self.scan_called += 1


class TestConnmanManagerImpl:
    @pytest.mark.asyncio
    async def test_setup(self, ovshell: testing.OpenVarioShellStub) -> None:
        # GIVEN
        bus = ovshell.os.stub_connect_bus()
        net_connman_manager = NetConnmanManagerStub()
        net_connman_manager.stub_set_technologies(
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
        bus.stub_register_interface("/", "net.connman.Manager", net_connman_manager)
        mgr = ConnmanManagerImpl(await ovshell.os.get_system_bus())

        # WHEN
        await mgr.setup()

        # THEN
        assert len(mgr.technologies) == 1

    @pytest.mark.asyncio
    async def test_scan_all(self, ovshell: testing.OpenVarioShellStub) -> None:
        # GIVEN
        bus = ovshell.os.stub_connect_bus()
        net_connman_manager = NetConnmanManagerStub()

        net_connman_manager.stub_set_technologies(
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

        bus.stub_register_interface("/", "net.connman.Manager", net_connman_manager)
        bus.stub_register_interface("/wifi", "net.connman.Technology", net_connman_tech)
        mgr = ConnmanManagerImpl(await ovshell.os.get_system_bus())
        await mgr.setup()

        # WHEN
        assert len(mgr.technologies) > 0
        scanned = await mgr.scan_all()

        # THEN
        assert scanned == 1  # only wifi is scanned
        assert net_connman_tech.scan_called == 1

    async def _setup_manager(self, ovshell: testing.OpenVarioShellStub) -> None:
        pass
