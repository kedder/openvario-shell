from typing import Any, Union

from dbus_next.service import ServiceInterface, method
from dbus_next.signature import SignatureType
from dbus_next import Variant, DBusError

from .api import ConnmanAgent, ConnmanManager


class ConnmanAgentInterface(ServiceInterface):
    """Interface for connman agent

    See https://git.kernel.org/pub/scm/network/connman/connman.git/tree/doc/agent-api.txt
    """

    def __init__(self, manager: ConnmanManager, impl: ConnmanAgent) -> None:
        super().__init__("net.connman.Agent")
        self._manager = manager
        self._impl = impl

    @method("RequestInput")
    async def request_input(
        self, service: "o", fields: "a{sv}",  # type: ignore
    ) -> "a{sv}":  # type: ignore
        print("REQUEST INPUT", service, self._drop_variants(fields))
        svc = await self._manager.get_service(service)
        if svc is None:
            raise DBusError(
                "net.connman.Agent.Error.Canceled", f"Cannot find service {service}"
            )

        plain_fields = unpack_variants(fields, SignatureType("a{sv}"))
        res = await self._impl.request_input(svc, plain_fields)
        raise DBusError("net.connman.Agent.Error.Canceled", f"Not implemented")

        return res


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
