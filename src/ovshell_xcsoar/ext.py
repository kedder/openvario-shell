from typing import Sequence
from ovshell import protocol


class XCSoarApp(protocol.App):
    name = "xcsoar"
    title = "XCSoar"
    description = "Tactical glide computer"
    priority = 90

    def __init__(self, app: protocol.OpenVarioShell) -> None:
        self.app = app

    def launch(self) -> None:
        pass


class XCSoarExtension(protocol.Extension):
    title = "XCSoar"

    def __init__(self, id: str, app: protocol.OpenVarioShell):
        self.id = id
        self.app = app
        self._init_settings()

    def list_apps(self) -> Sequence[protocol.App]:
        return [XCSoarApp(self.app)]

    def _init_settings(self) -> None:
        config = self.app.settings
        config.setdefault("xcsoar.path", "/opt/XCSoar/bin/xcsoar")
