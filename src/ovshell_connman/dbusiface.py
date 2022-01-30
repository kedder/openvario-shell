from typing import Any, Callable, Protocol

from dbus_next import Variant


class ConnmanManagerProxyInterface(Protocol):
    """D-Bus inteface for net.connman.Manager"""

    async def call_get_technologies(self) -> list[tuple[str, dict[str, Any]]]:
        pass

    async def call_get_properties(self) -> dict[str, Variant]:
        pass

    async def call_get_services(self) -> list[tuple[str, dict[str, Any]]]:
        pass

    async def call_register_agent(self, path: str) -> None:
        pass

    def on_property_changed(self, handler: Callable[[str, Variant], None]) -> None:
        pass

    def on_services_changed(
        self, handler: Callable[[list[tuple[str, dict[str, Variant]]], list[str]], None]
    ) -> None:
        pass

    def on_technology_added(
        self, handler: Callable[[str, dict[str, Any]], None]
    ) -> None:
        pass

    def on_technology_removed(self, handler: Callable[[str], None]) -> None:
        pass

    def off_property_changed(self, handler: Callable[[str, Variant], None]) -> None:
        pass

    def off_services_changed(
        self, handler: Callable[[list[tuple[str, dict[str, Variant]]], list[str]], None]
    ) -> None:
        pass

    def off_technology_added(
        self, handler: Callable[[str, dict[str, Any]], None]
    ) -> None:
        pass

    def off_technology_removed(self, handler: Callable[[str], None]) -> None:
        pass


class ConnmanServiceProxyInterface(Protocol):
    """D-Bus inteface for net.connman.Service"""

    async def call_connect(self) -> None:
        pass

    async def call_disconnect(self) -> None:
        pass

    async def call_remove(self) -> None:
        pass

    async def call_get_properties(self) -> dict[str, Variant]:
        pass

    def on_property_changed(self, handler: Callable[[str, Variant], None]) -> None:
        pass

    def off_property_changed(self, handler: Callable[[str, Variant], None]) -> None:
        pass


class ConnmanTechnologyProxyInterface(Protocol):
    async def call_set_property(self, prop: str, value: Variant) -> None:
        pass

    async def call_scan(self) -> None:
        pass
