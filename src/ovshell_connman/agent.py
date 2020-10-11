from typing import Dict, Any

from ovshell import api

from .api import ConnmanAgent, ConnmanService, Canceled


class ConnmanAgentImpl(ConnmanAgent):
    def __init__(self, screen: api.ScreenManager) -> None:
        self.screen = screen

    def report_error(self, service: ConnmanService, error: str) -> None:
        print("ERROR: ", error)

    async def request_input(
        self, service: ConnmanService, fields: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        print("Requesting: ", fields)
        # {'Passphrase': {'Type': 'psk', 'Requirement': 'mandatory'}}
        # {'Passphrase': {'Type': 'psk', 'Requirement': 'mandatory', 'Alternates': ['WPS']}, 'WPS': {'Type': 'wpspin', 'Requirement': 'alternate'}}
        raise Canceled()
        return {}

    def cancel(self) -> None:
        print("CANCEL")
