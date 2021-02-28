import asyncio

import pytest

from ovshell import testing
from ovshell_connman.api import ConnmanService, ConnmanTechnology
from ovshell_connman.app import ConnmanManagerActivity, ConnmanManagerApp
from ovshell_connman.app import ConnmanServiceState
from tests.fixtures.urwid import UrwidMock

from .stubs import ConnmanManagerStub


class TestConnmanManagerApp:
    ovshell: testing.OpenVarioShellStub

    @pytest.fixture(autouse=True)
    def setup(self, ovshell: testing.OpenVarioShellStub) -> None:
        self.ovshell = ovshell

    @pytest.mark.asyncio
    async def test_launch(self) -> None:
        # GIVEN
        app = ConnmanManagerApp(self.ovshell)

        # WHEN
        app.launch()

        dialog = self.ovshell.screen.stub_dialog()
        assert dialog is not None
        assert "Connecting" in dialog.title
        self.ovshell.os.stub_connect_bus()

        await asyncio.sleep(0)

        # THEN
        activity = self.ovshell.screen.stub_top_activity()
        assert isinstance(activity, ConnmanManagerActivity)

    @pytest.mark.asyncio
    async def test_failed_dbus(self) -> None:
        # GIVEN
        app = ConnmanManagerApp(self.ovshell)

        # WHEN
        app.launch()
        self.ovshell.os.stub_fail_bus()
        await asyncio.sleep(0)

        # THEN
        dialog = self.ovshell.screen.stub_dialog()
        assert dialog is not None
        assert dialog.title == "Unable to connect"


class TestConnmanManagerActivity:
    ovshell: testing.OpenVarioShellStub
    manager: ConnmanManagerStub
    activity: ConnmanManagerActivity

    @pytest.fixture(autouse=True)
    def setup_activity(self, ovshell: testing.OpenVarioShellStub) -> None:
        self.ovshell = ovshell
        self.manager = ConnmanManagerStub()
        self.activity = ConnmanManagerActivity(ovshell, self.manager)
        self.urwid = UrwidMock()

        self.wifi_tech = ConnmanTechnology(
            path="/tech-path", name="WiFi", type="wifi", connected=False, powered=False,
        )
        self.svc = ConnmanService(
            path="/svc-path",
            auto_connect=False,
            favorite=False,
            name="Service One",
            security=["wps"],
            state=ConnmanServiceState.IDLE,
            strength=32,
            type="wifi",
        )

    @pytest.mark.asyncio
    async def test_initial_view(self) -> None:
        # GIVEN
        wdg = self.activity.create()
        self.activity.activate()
        await asyncio.sleep(0)

        # WHEN
        rendered = self.urwid.render(wdg)

        # THEN
        assert "Network connections" in rendered
        assert "Signal" in rendered
        assert "Service" in rendered
        assert "State" in rendered

    @pytest.mark.asyncio
    async def test_techs_displayed(self) -> None:
        # GIVEN
        wdg = self.activity.create()
        self.activity.activate()
        self.manager.stub_add_technology(self.wifi_tech)
        await asyncio.sleep(0)

        # WHEN
        rendered = self.urwid.render(wdg)

        # THEN
        assert "Technologies" in rendered
        assert "WiFi" in rendered
        assert "Scan" in rendered

    @pytest.mark.asyncio
    async def test_tech_power_on(self) -> None:
        # GIVEN
        wdg = self.activity.create()
        self.activity.activate()
        self.manager.stub_add_technology(self.wifi_tech)
        await asyncio.sleep(0)

        # WHEN
        # Press the scan button
        self.urwid.keypress(wdg, ["up", "up", "enter"])
        await asyncio.sleep(0)

        # THEN
        rendered = self.urwid.render(wdg)
        assert "[X] WiFi" in rendered
        assert self.manager.stub_get_log() == ["Power /tech-path on"]

    @pytest.mark.asyncio
    async def test_scan(self) -> None:
        # GIVEN
        wdg = self.activity.create()
        self.activity.activate()
        self.manager.stub_add_technology(self.wifi_tech)
        await asyncio.sleep(0)
        rendered = self.urwid.render(wdg)

        # WHEN
        # Press the scan button
        self.urwid.keypress(wdg, ["up", "enter"])
        await asyncio.sleep(0)

        # THEN
        rendered = self.urwid.render(wdg)
        assert self.manager.stub_get_log() == ["Scanning..."]

        self.manager.stub_scan_completed()
        await asyncio.sleep(0)

        assert self.manager.stub_get_log() == ["Scanning...", "Scanning completed"]

    @pytest.mark.asyncio
    async def test_show_services(self) -> None:
        # GIVEN
        wdg = self.activity.create()
        self.activity.activate()

        # WHEN
        self.manager.stub_add_service(self.svc)
        await asyncio.sleep(0)

        # THEN
        rendered = self.urwid.render(wdg)

        # Signal is displayed
        assert "   ■■" in rendered
        assert "Service One" in rendered
        assert "idle" in rendered

    @pytest.mark.asyncio
    async def test_service_connect_regular(self) -> None:
        # GIVEN
        wdg = self.activity.create()
        self.activity.activate()

        assert not self.svc.favorite
        assert self.svc.state == ConnmanServiceState.IDLE
        self.manager.stub_add_service(self.svc)
        await asyncio.sleep(0)

        # WHEN
        self.urwid.keypress(wdg, ["enter"])
        await asyncio.sleep(0)

        assert self.manager.stub_get_log() == ["Connect to /svc-path"]

    @pytest.mark.asyncio
    async def test_service_connect_favorite(self) -> None:
        # GIVEN
        wdg = self.activity.create()
        self.activity.activate()

        self.svc.favorite = True
        self.manager.stub_add_service(self.svc)
        await asyncio.sleep(0)

        # WHEN
        self.urwid.keypress(wdg, ["enter"])
        await asyncio.sleep(0)

        # WHEN
        dialog = self.ovshell.screen.stub_dialog()
        assert dialog is not None
        assert {"Connect", "Forget"} == dialog.buttons.keys()
        dialog.stub_press_button("Connect")
        await asyncio.sleep(0)
        assert self.manager.stub_get_log() == ["Connect to /svc-path"]

    @pytest.mark.asyncio
    async def test_service_disconnect(self) -> None:
        # GIVEN
        wdg = self.activity.create()
        self.activity.activate()

        self.svc.favorite = True
        self.svc.state = ConnmanServiceState.ONLINE
        self.manager.stub_add_service(self.svc)
        await asyncio.sleep(0)

        # WHEN
        self.urwid.keypress(wdg, ["enter"])
        await asyncio.sleep(0)

        # WHEN
        dialog = self.ovshell.screen.stub_dialog()
        assert dialog is not None
        assert {"Disconnect", "Forget"} == dialog.buttons.keys()
        dialog.stub_press_button("Disconnect")
        await asyncio.sleep(0)
        assert self.manager.stub_get_log() == ["Disconnect /svc-path"]

    @pytest.mark.asyncio
    async def test_service_forget(self) -> None:
        # GIVEN
        wdg = self.activity.create()
        self.activity.activate()

        self.svc.favorite = True
        self.svc.state = ConnmanServiceState.ONLINE
        self.manager.stub_add_service(self.svc)
        await asyncio.sleep(0)

        # WHEN
        self.urwid.keypress(wdg, ["enter"])
        await asyncio.sleep(0)

        # WHEN
        dialog = self.ovshell.screen.stub_dialog()
        assert dialog is not None
        assert {"Disconnect", "Forget"} == dialog.buttons.keys()
        dialog.stub_press_button("Forget")
        await asyncio.sleep(0)
        assert self.manager.stub_get_log() == ["Remove /svc-path"]

    @pytest.mark.asyncio
    async def test_teardown_on_exit(self) -> None:
        # WHEN
        self.activity.destroy()

        # THEN
        assert self.manager.stub_get_log() == ["Teardown"]
