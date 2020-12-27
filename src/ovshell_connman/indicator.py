from dbus_next.message_bus import BaseMessageBus

from ovshell import api

from .api import ConnmanManager, ConnmanService, ConnmanServiceState
from .manager import ConnmanManagerImpl

INDICATOR_ID = "connman"


class ConnmanServiceIndicator:
    _manager: ConnmanManager

    def __init__(self, screen: api.ScreenManager, manager: ConnmanManager) -> None:
        self._screen = screen
        self._manager = manager

    async def start(self):
        self._manager.on_services_changed(self._handle_svcs_changed)
        await self._manager.setup()

    def _handle_svcs_changed(self) -> None:
        svcs = self._manager.services
        if not svcs:
            self._no_connection()
            return

        top_svc = svcs[0]

        indicated_states = [
            ConnmanServiceState.ASSOCIATION,
            ConnmanServiceState.CONFIGURATION,
            ConnmanServiceState.READY,
            ConnmanServiceState.ONLINE,
        ]

        if top_svc.state not in indicated_states:
            self._no_connection()
            return

        self._indicate_connection(top_svc)

    def _indicate_connection(self, svc: ConnmanService) -> None:
        color = "ind normal"
        if svc.state == ConnmanServiceState.ASSOCIATION:
            color = "ind error"
        elif svc.state == ConnmanServiceState.CONFIGURATION:
            color = "ind error"
        elif svc.state == ConnmanServiceState.READY:
            color = "ind warning"
        elif svc.state == ConnmanServiceState.ONLINE:
            color = "ind good"

        self._screen.set_indicator(
            INDICATOR_ID, ["(", (color, svc.name), ")"], api.IndicatorLocation.RIGHT, 20
        )

    def _no_connection(self) -> None:
        self._screen.remove_indicator(INDICATOR_ID)


async def start_indicator(screen: api.ScreenManager, bus: BaseMessageBus) -> None:
    manager = ConnmanManagerImpl(bus)
    indicator = ConnmanServiceIndicator(screen, manager)
    await indicator.start()
