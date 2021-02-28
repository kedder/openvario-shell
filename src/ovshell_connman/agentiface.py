from typing import Any, Union

from dbus_next import DBusError, Variant
from dbus_next.message_bus import BaseMessageBus
from dbus_next.service import ServiceInterface, method
from dbus_next.signature import SignatureType

from . import model
from .api import Canceled, ConnmanAgent


class ConnmanAgentInterface(ServiceInterface):
    """Interface for connman agent

    See https://git.kernel.org/pub/scm/network/connman/connman.git/tree/doc/agent-api.txt
    """

    def __init__(self, impl: ConnmanAgent, bus: BaseMessageBus) -> None:
        super().__init__("net.connman.Agent")
        self._bus = bus
        self._impl = impl

    async def register(self) -> None:
        introspection = await self._bus.introspect("net.connman", "/")
        proxy = self._bus.get_proxy_object("net.connman", "/", introspection)
        iface = proxy.get_interface("net.connman.Manager")
        self._bus.export("/org/ovshell/connman", self)
        await iface.call_register_agent("/org/ovshell/connman")

    @method("Release")
    def release(self):
        """This method gets called when the service daemon
        unregisters the agent. An agent can use it to do
        cleanup tasks. There is no need to unregister the
        agent, because when this method gets called it has
        already been unregistered.
        """
        raise NotImplementedError()  # pragma: nocover

    @method("ReportError")
    def report_error(self, service: "o", error: "s"):  # type: ignore
        """This method gets called when an error has to be
        reported to the user.

        A special return value can be used to trigger a
        retry of the failed transaction.

        Possible Errors: net.connman.Agent.Error.Retry
        """
        raise NotImplementedError()  # pragma: nocover

    @method("ReportPeerError")
    def report_peer_error(peer: "o", error: "s"):  # type: ignore
        """This method gets called when an error has to be
        reported to the user about a peer connection.

        A special return value can be used to trigger a
        retry of the failed transaction.

        Possible Errors: net.connman.Agent.Error.Retry
        """
        raise NotImplementedError()  # pragma: nocover

    @method("RequestBrowser")
    def request_browser(service: "o", url: "s"):  # type: ignore
        """This method gets called when it is required
        to ask the user to open a website to proceed
        with login handling.

        This can happen if connected to a hotspot portal
        page without WISPr support.

        Possible Errors: net.connman.Agent.Error.Canceled
        """
        raise NotImplementedError()  # pragma: nocover

    @method("RequestInput")
    async def request_input(
        self, service: "o", fields: "a{sv}",  # type: ignore
    ) -> "a{sv}":  # type: ignore
        """This method gets called when trying to connect to
        a service and some extra input is required. For
        example a passphrase or the name of a hidden network.

        The return value should be a dictionary where the
        keys are the field names and the values are the
        actual fields. Alternatively an error indicating that
        the request got canceled can be returned.
        OperationAborted will be return on a successful
        cancel request.

        Most common return field names are "Name" and of
        course "Passphrase".

        The dictionary arguments contains field names with
        their input parameters.

        In case of WISPr credentials requests and if the user
        prefers to login through the browser by himself, agent
        will have to return a LaunchBrowser error (see below).

        Possible Errors: net.connman.Agent.Error.Canceled
                 net.connman.Agent.Error.LaunchBrowser
        """

        # Fetch the service properties
        return await agent_request_input(self._bus, self._impl, service, fields)

    @method("RequestPeerAuthorization")
    def request_peer_authorization(self, peer: "o", fields: "a{sv}") -> "a{sv}":  # type: ignore
        """This method gets called when trying to connect to a
        peer or when an incoming peer connection is requested,
        for which some extra input is required. In this case,
        it will only deal with WPS input as well as accepting
        or rejecting an incoming connection.

        The return value should be a dictionary where the
        keys are the field names and the values are the
        actual fields. Alternatively an error indicating that
        the request got canceled or rejected can be returned.

        The dictionary arguments contains field names with
        their input parameters.

        Possible Errors: net.connman.Agent.Error.Canceled
                         net.connman.Agent.Error.Rejected
        """
        raise NotImplementedError()  # pragma: nocover

    @method("Cancel")
    def cancel(self):
        """This method gets called to indicate that the agent
        request failed before a reply was returned.
        """


async def agent_request_input(bus: BaseMessageBus, impl: ConnmanAgent, service, fields):
    introspection = await bus.introspect("net.connman", service)
    proxy = bus.get_proxy_object("net.connman", service, introspection)
    iface = proxy.get_interface("net.connman.Service")
    props = await iface.call_get_properties()
    svc = model.create_service_from_props(service, props)

    plain_fields = unpack_variants(fields, "a{sv}")
    try:
        res = await impl.request_input(svc, plain_fields)
    except Canceled as e:
        raise DBusError("net.connman.Agent.Error.Canceled", str(e))
    varres = {k: Variant("s", v) for k, v in res.items() if v is not None}
    return varres


def unpack_variants(var: Union[Variant, Any], tp: SignatureType = None) -> Any:
    if not isinstance(var, Variant):
        if tp is None:
            return var
        var = Variant(tp, var)

    if var.type.token == "(":
        return [unpack_variants(v, t) for t, v in zip(var.type.children, var.value)]
    if var.type.token == "a":
        assert len(var.type.children) == 1
        childtype = var.type.children[0]
        if childtype.token == "{":
            kt, vt = childtype.children
            # a dict
            return {
                unpack_variants(k, kt): unpack_variants(v, vt)
                for k, v in var.value.items()
            }
        if childtype.token == "y":
            # array of bytes, special case
            return var.value

        # This is a list of items
        return [unpack_variants(v, childtype) for v in var.value]
    return var.value
