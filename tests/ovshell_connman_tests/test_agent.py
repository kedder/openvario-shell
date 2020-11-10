import asyncio

import pytest

from ovshell import testing
from ovshell_connman.agent import ConnmanAgentImpl, ConnmanInputActivity
from ovshell_connman.api import ConnmanService


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
            state="on",
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
