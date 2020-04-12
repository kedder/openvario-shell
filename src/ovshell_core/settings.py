from typing import Optional, cast, Sequence, Tuple

from ovshell import protocol
from ovshell.ui.settings import StaticChoiceSetting


class RotationSetting(StaticChoiceSetting):
    title = "Screen rotation"
    config_key = "core.screen_orientation"
    priority = 80

    def __init__(self, app: protocol.OpenVarioShell):
        self.app = app
        super().__init__()

    def read(self) -> Optional[str]:
        return cast(Optional[str], self.app.settings.get(self.config_key))

    def store(self, value: Optional[str]) -> None:
        self.app.settings.set(self.config_key, value, save=True)

    def get_choices(self) -> Sequence[Tuple[str, str]]:
        return [
            ("0", "Landscape"),
            ("1", "Portrait (90)"),
            ("2", "Landscape (180)"),
            ("3", "Portrait (270)"),
        ]


class LanguageSetting(StaticChoiceSetting):
    title = "Language"
    config_key = "core.language"
    priority = 70

    def __init__(self, app: protocol.OpenVarioShell):
        self.app = app
        super().__init__()

    def read(self) -> Optional[str]:
        return cast(Optional[str], self.app.settings.get(self.config_key))

    def store(self, value: Optional[str]) -> None:
        self.app.settings.set(self.config_key, value, save=True)

    def get_choices(self) -> Sequence[Tuple[str, str]]:
        return [
            ("en_EN.UTF-8", "English"),
            ("de_DE.UTF-8", "German"),
            ("fr_FR.UTF-8", "French"),
            ("ru_RU.UTF-8", "Russian"),
        ]
