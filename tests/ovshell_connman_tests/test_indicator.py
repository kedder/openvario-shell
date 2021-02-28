import asyncio

import pytest

from ovshell import api, testing
from ovshell_connman.api import ConnmanService, ConnmanServiceState
from ovshell_connman.indicator import ConnmanServiceIndicator, start_indicator

from .stubs import ConnmanManagerStub, NetConnmanManagerStub


class TestConnmanServiceIndicator:
    @pytest.fixture(autouse=True)
    def setup(self, ovshell: testing.OpenVarioShellStub) -> None:
        self.ovshell = ovshell
        self.manager = ConnmanManagerStub()
        self.indicator = ConnmanServiceIndicator(ovshell.screen, self.manager)

        self.svc1 = ConnmanService(
            path="/svc1-path",
            auto_connect=False,
            favorite=False,
            name="Service One",
            security=["wps"],
            state=ConnmanServiceState.IDLE,
            strength=32,
            type="wifi",
        )
        self.svc2 = ConnmanService(
            path="/svc2-path",
            auto_connect=False,
            favorite=False,
            name="Service Two",
            security=["wps"],
            state=ConnmanServiceState.IDLE,
            strength=54,
            type="wifi",
        )

    @pytest.mark.asyncio
    async def test_start(self) -> None:
        # WHEN
        await self.indicator.start()
        await asyncio.sleep(0)

        # THEN
        assert self.ovshell.screen.stub_get_indicator("connman") is None

    @pytest.mark.asyncio
    async def test_association(self) -> None:
        # GIVEN
        await self.indicator.start()
        await asyncio.sleep(0)

        # WHEN
        self.svc1.state = ConnmanServiceState.ASSOCIATION
        self.manager.stub_add_service(self.svc1)

        # THEN
        ind = self.ovshell.screen.stub_get_indicator("connman")
        assert ind is not None
        assert ind.location == api.IndicatorLocation.RIGHT
        assert ind.markup == ["(", ("ind error", "Service One"), ")"]

    @pytest.mark.asyncio
    async def test_change_service(self) -> None:
        # GIVEN
        await self.indicator.start()
        await asyncio.sleep(0)
        self.svc1.state = ConnmanServiceState.ASSOCIATION
        self.svc2.state = ConnmanServiceState.READY
        self.manager.stub_add_service(self.svc1)

        # WHEN
        self.manager.stub_set_services([self.svc2, self.svc1])

        # THEN
        ind = self.ovshell.screen.stub_get_indicator("connman")
        assert ind is not None
        assert ind.markup == ["(", ("ind warning", "Service Two"), ")"]

    @pytest.mark.asyncio
    async def test_change_state(self) -> None:
        # GIVEN
        await self.indicator.start()
        await asyncio.sleep(0)
        self.svc1.state = ConnmanServiceState.ASSOCIATION
        self.manager.stub_add_service(self.svc1)

        # WHEN
        self.svc1.state = ConnmanServiceState.ONLINE
        self.manager.stub_service_prop_changed(self.svc1)

        # THEN
        ind = self.ovshell.screen.stub_get_indicator("connman")
        assert ind is not None
        assert ind.markup == ["(", ("ind good", "Service One"), ")"]

    @pytest.mark.asyncio
    async def test_no_services(self) -> None:
        # GIVEN
        await self.indicator.start()
        await asyncio.sleep(0)
        self.svc1.state = ConnmanServiceState.CONFIGURATION
        self.manager.stub_add_service(self.svc1)

        # WHEN
        self.manager.stub_set_services([])

        # THEN
        ind = self.ovshell.screen.stub_get_indicator("connman")
        assert ind is None

    @pytest.mark.asyncio
    async def test_not_indicated_state(self) -> None:
        # GIVEN
        await self.indicator.start()
        await asyncio.sleep(0)
        self.svc1.state = ConnmanServiceState.FAILURE

        # WHEN
        self.manager.stub_add_service(self.svc1)

        # THEN
        ind = self.ovshell.screen.stub_get_indicator("connman")
        assert ind is None

    @pytest.mark.asyncio
    async def test_start_indicator(self) -> None:
        bus = self.ovshell.os.stub_connect_bus()
        net_connman_manager = NetConnmanManagerStub()
        bus.stub_register_interface("/", "net.connman.Manager", net_connman_manager)

        task = asyncio.create_task(start_indicator(self.ovshell.screen, bus))
        await asyncio.sleep(0)

        assert not task.done()
        signals = net_connman_manager.stub_get_signals()
        assert signals.keys() == {
            "property_changed",
            "services_changed",
            "technology_added",
            "technology_removed",
        }

        task.cancel()
