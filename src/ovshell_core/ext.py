from typing import Sequence
from ovshell import protocol

from ovshell_core import settings


class CoreExtension(protocol.Extension):
    title = "Core"

    def __init__(self, id: str, shell: protocol.OpenVarioShell):
        self.id = id
        self.shell = shell
        self._init_settings()

    def list_settings(self) -> Sequence[protocol.Setting]:
        return [
            settings.RotationSetting(self.shell),
            settings.LanguageSetting(self.shell),
        ]

    def _init_settings(self) -> None:
        config = self.shell.settings
        config.setdefault("core.screen_orientation", "0")
        config.setdefault("core.language", "en_EN.UTF-8")
