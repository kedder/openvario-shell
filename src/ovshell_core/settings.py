import os
import subprocess
from typing import Optional, Sequence, Tuple

from ovshell import api
from ovshell.ui.settings import StaticChoiceSetting
from ovshell_core import rotation


class RotationSetting(StaticChoiceSetting):
    title = "Screen rotation"
    config_key = "core.screen_orientation"
    priority = 80

    def __init__(self, shell: api.OpenVarioShell):
        self.shell = shell
        super().__init__()

    def read(self) -> Optional[str]:
        return self.shell.settings.get(self.config_key, str)

    def store(self, value: Optional[str]) -> None:
        self._apply_rotation(value or "0")
        self.shell.settings.set(self.config_key, value, save=True)

    def get_choices(self) -> Sequence[Tuple[str, str]]:
        return rotation.get_rotations()

    def _apply_rotation(self, new_rotation: str) -> None:
        rotation.apply_rotation(self.shell.os, new_rotation)


class LanguageSetting(StaticChoiceSetting):
    title = "Language"
    config_key = "core.language"
    priority = 70

    def __init__(self, shell: api.OpenVarioShell):
        self.shell = shell
        super().__init__()

    def read(self) -> Optional[str]:
        return self.shell.settings.get(self.config_key, str)

    def store(self, value: Optional[str]) -> None:
        self.shell.settings.set(self.config_key, value, save=True)

    def get_choices(self) -> Sequence[Tuple[str, str]]:
        return [
            ("en_EN.UTF-8", "English"),
            ("de_DE.UTF-8", "Deutsch"),
            ("fr_FR.UTF-8", "Française"),
            ("it_IT.UTF-8", "Italiano"),
            ("hu_HU.UTF-8", "Magyar"),
            ("pl_PL.UTF-8", "Polski"),
            ("cs_CZ.UTF-8", "Český"),
            ("sk_SK.UTF-8", "Slovenský"),
            ("lt_LT.UTF-8", "Lietuvių"),
            ("ru_RU.UTF-8", "Русский"),
        ]


class ConsoleFontSetting(StaticChoiceSetting):
    title = "Font"
    priority = 50
    config_key = "core.font"

    def __init__(self, shell: api.OpenVarioShell):
        self.shell = shell
        super().__init__()

    def read(self) -> Optional[str]:
        return self.shell.settings.get(self.config_key, str)

    def store(self, value: Optional[str]) -> None:
        if value is not None:
            apply_font(self.shell.os, value)
        self.shell.settings.set(self.config_key, value, save=True)

    def get_choices(self) -> Sequence[Tuple[str, str]]:
        return [
            ("zap-ext-vga09.psf", "9x8 bold"),
            ("zap-ext-light16.psf", "16x8 light"),
            ("zap-ext-vga16.psf", "16x8 bold"),
            ("zap-ext-light18.psf", "18x8 light"),
            ("zap-ext-light20.psf", "20x10 light"),
            ("zap-ext-light24.psf", "24x10 light"),
        ]


class ScreenBrightnessSetting(StaticChoiceSetting):
    title = "Screen brightness"
    priority = 75
    brightness_fname = "//sys/class/backlight/lcd/brightness"

    def __init__(self, shell: api.OpenVarioShell):
        self.shell = shell
        super().__init__()

    def read(self) -> Optional[str]:
        br_fname = self.shell.os.path(self.brightness_fname)
        if not os.path.exists(br_fname):
            return None

        with open(br_fname, "r") as f:
            br = f.read()

        return br.strip()

    def store(self, value: Optional[str]) -> None:
        if value is None:
            return

        br_fname = self.shell.os.path(self.brightness_fname)

        if not os.path.exists(br_fname):
            return

        with open(br_fname, "w") as f:
            f.write(value)

    def get_choices(self) -> Sequence[Tuple[str, str]]:
        return [
            ("2", "20%"),
            ("3", "30%"),
            ("4", "40%"),
            ("5", "50%"),
            ("6", "60%"),
            ("7", "70%"),
            ("8", "80%"),
            ("9", "90%"),
            ("10", "100%"),
        ]


class AutostartAppSetting(StaticChoiceSetting):
    title = "Autostart application"
    priority = 68
    config_key = "ovshell.autostart_app"

    def __init__(self, shell: api.OpenVarioShell):
        self.shell = shell
        super().__init__()

    def read(self) -> Optional[str]:
        return self.shell.settings.get(self.config_key, str, "")

    def store(self, value: Optional[str]) -> None:
        self.shell.settings.set(self.config_key, value, save=True)

    def get_choices(self) -> Sequence[Tuple[str, str]]:
        choices = [("", "Main Menu")]
        for appinfo in self.shell.apps.list():
            choices.append((appinfo.id, appinfo.app.title))

        return choices


class AutostartTimeoutSetting(StaticChoiceSetting):
    title = "Autostart timeout"
    priority = 67
    config_key = "ovshell.autostart_timeout"

    def __init__(self, shell: api.OpenVarioShell):
        self.shell = shell
        super().__init__()

    def read(self) -> Optional[str]:
        return str(self.shell.settings.get(self.config_key, int, 0))

    def store(self, value: Optional[str]) -> None:
        self.shell.settings.set(self.config_key, int(value or 0), save=True)

    def get_choices(self) -> Sequence[Tuple[str, str]]:
        return [
            ("0", "Immediately"),
            ("1", "1s"),
            ("3", "3s"),
            ("5", "5s"),
            ("10", "10s"),
            ("30", "30s"),
        ]


def apply_font(os: api.OpenVarioOS, font_name: str) -> None:
    setfont = os.path("//usr/bin/setfont")
    subprocess.run([setfont, font_name], check=True)
