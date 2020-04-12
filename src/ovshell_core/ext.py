from typing import Sequence
from ovshell import protocol

from ovshell_core import settings


class CoreExtension(protocol.Extension):
    title = "Core"

    def __init__(self, id: str, app: protocol.OpenVarioShell):
        self.id = id
        self.app = app

    def list_settings(self) -> Sequence[protocol.Setting]:
        return [settings.RotationSetting(self.app), settings.LanguageSetting(self.app)]
