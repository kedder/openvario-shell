from typing import Dict, Any

from .api import ConnmanAgent, ConnmanService


class ConnmanAgentImpl(ConnmanAgent):
    def report_error(self, service: ConnmanService, error: str) -> None:
        print("ERROR: ", error)

    async def request_input(
        self, service: ConnmanService, fields: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        print("Requesting: ", fields)
        return {}

    def cancel(self) -> None:
        print("CANCEL")
