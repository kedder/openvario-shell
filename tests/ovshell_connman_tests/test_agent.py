import asyncio

import pytest

from ovshell import testing
from ovshell_connman.agent import ConnmanAgentImpl, ConnmanInputActivity
from ovshell_connman.api import ConnmanService, ConnmanServiceState
from tests.fixtures.urwid import UrwidMock


class TestConnmanAgentImpl:
    @pytest.mark.asyncio
    async def test_request_input(self, ovshell: testing.OpenVarioShellStub) -> None:
        # GIVEN
        agent = ConnmanAgentImpl(ovshell.screen)
        service = ConnmanService(
            path="/path",
            auto_connect=True,
            favorite=True,
            name="Test",
            security=["WPS"],
            state=ConnmanServiceState.ONLINE,
            strength=84,
            type="wifi",
        )
        fields = {"Passphrase": {"Type": "psk", "Requirement": "mandatory"}}

        # WHEN
        task = asyncio.create_task(agent.request_input(service, fields))
        await asyncio.sleep(0)

        # THEN
        activity = ovshell.screen.stub_top_activity()
        assert isinstance(activity, ConnmanInputActivity)
        activity.done.set_result({})

        # Make sure task request_input returns
        res = await task
        assert res == {}


class TestConnmanInputActivity:
    @pytest.fixture(autouse=True)
    def setup_service(self) -> None:
        self.service = ConnmanService(
            path="/path",
            auto_connect=True,
            favorite=True,
            name="Sample Service",
            security=["WPS"],
            state=ConnmanServiceState.ONLINE,
            strength=84,
            type="wifi",
        )

    @pytest.mark.asyncio
    async def test_password_input(self, ovshell: testing.OpenVarioShellStub) -> None:
        urwid_mock = UrwidMock()
        fields = {"Passphrase": {"Type": "psk", "Requirement": "mandatory"}}
        act = ConnmanInputActivity(ovshell.screen, self.service, fields)
        ovshell.screen.push_activity(act)

        wdg = act.create()
        rendered = urwid_mock.render(wdg)

        assert "Sample Service" in rendered
        assert "Passphrase" in rendered
        assert "Confirm" in rendered

        # Enter a password
        urwid_mock.keypress(wdg, ["5", "e", "c", "r", "e", "t"])
        urwid_mock.keypress(wdg, ["down", "enter"])

        res = await act.done
        assert res == {"Passphrase": "5ecret"}
