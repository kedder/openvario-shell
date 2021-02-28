from typing import Any, Dict, List

import pytest
from dbus_next import Variant

from ovshell import testing
from ovshell_connman.agentiface import ConnmanAgentInterface, agent_request_input
from ovshell_connman.agentiface import unpack_variants
from ovshell_connman.api import ConnmanAgent, ConnmanService

from .stubs import NetConnmanManagerStub, NetConnmanServiceStub


def test_unpack_variants() -> None:
    assert unpack_variants("plain") == "plain"

    inp = Variant("i", 5)
    assert unpack_variants(inp) == 5

    inp = Variant("a{sv}", {"one": Variant("i", 1)})
    assert unpack_variants(inp) == {"one": 1}

    inp = Variant("(sv)", ["foo", Variant("u", 5)])
    assert unpack_variants(inp) == ["foo", 5]

    inp = Variant("(asv)", [["foo"], Variant("u", 5)])
    assert unpack_variants(inp) == [["foo"], 5]

    inp = Variant("(avv)", [[Variant("s", "foo")], Variant("u", 5)])
    assert unpack_variants(inp) == [["foo"], 5]

    inp = Variant("aav", [[Variant("s", "foo"), Variant("u", 5)]])
    assert unpack_variants(inp) == [["foo", 5]]


def test_unpack_variants_explicit() -> None:
    inp = {"one": Variant("i", 1)}
    assert unpack_variants(inp, "a{sv}") == {"one": 1}


class ConnmanAgentStub(ConnmanAgent):
    _log: List[str]

    def __init__(self) -> None:
        self._log = []

    def report_error(self, service: ConnmanService, error: str) -> None:
        """Display error message to the user"""
        self._log.append(f"Error for {service.path}: {error}")

    async def request_input(
        self, service: ConnmanService, fields: Dict[str, Dict[str, str]]
    ) -> Dict[str, Any]:
        """Request input from the user"""
        self._log.append(f"Request input {service.path}")
        return {n: "input" for n, v in fields.items()}

    def cancel(self) -> None:
        """Inform that operation was canceled"""
        self._log.append("Cancel")


class TestConnmanAgentInterface:
    @pytest.fixture(autouse=True)
    def setup(self, ovshell: testing.OpenVarioShellStub) -> None:
        self.bus = ovshell.os.stub_connect_bus()
        self.net_connman_manager = NetConnmanManagerStub()
        self.bus.stub_register_interface(
            "/", "net.connman.Manager", self.net_connman_manager
        )
        self.agent = ConnmanAgentStub()
        self.agentiface = ConnmanAgentInterface(self.agent, self.bus)

        self.svc_iface = NetConnmanServiceStub()
        self.bus.stub_register_interface("/svc1", "net.connman.Service", self.svc_iface)

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
    async def test_register(self) -> None:
        # WHEN
        await self.agentiface.register()

        # THEN
        exported = self.bus.stub_get_exported()
        assert exported.keys() == {"/org/ovshell/connman"}

    @pytest.mark.asyncio
    async def test_agent_request_input(self) -> None:
        # GIVEN
        self.svc_iface.stub_properties_changed(self.sample_service_props)

        # WHEN
        inp = Variant("a{sv}", {"one": Variant("i", 1)})
        res = await agent_request_input(self.bus, self.agent, "/svc1", inp)
        assert res == {"one": Variant("s", "input")}
