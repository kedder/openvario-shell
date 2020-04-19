from typing import Optional, Sequence, Tuple
import re
import subprocess

from ovshell import protocol
from ovshell.ui.settings import StaticChoiceSetting


class RotationSetting(StaticChoiceSetting):
    title = "Screen rotation"
    config_key = "core.screen_orientation"
    priority = 80

    def __init__(self, shell: protocol.OpenVarioShell):
        self.shell = shell
        super().__init__()

    def read(self) -> Optional[str]:
        return self.shell.settings.get(self.config_key, str)

    def store(self, value: Optional[str]) -> None:
        self._apply_rotation(value or "0")
        self.shell.settings.set(self.config_key, value, save=True)

    def get_choices(self) -> Sequence[Tuple[str, str]]:
        return [
            ("0", "Landscape"),
            ("1", "Portrait (90°)"),
            ("2", "Landscape (180°)"),
            ("3", "Portrait (270°)"),
        ]

    def _apply_rotation(self, rotation: str) -> None:
        os = self.shell.os
        rchar = rotation.encode()

        if not os.file_exists("/boot/config.uEnv"):
            os.mount_boot()

        uenvconf = os.read_file("/boot/config.uEnv")
        uenvconf = re.sub(rb"rotation=[0-3]", b"rotation=" + rchar, uenvconf)
        os.write_file("/boot/config.uEnv", uenvconf)

        # For some weird reason 90 degree rotation is inverted for fbcon
        fbcon_rotmap = {
            "0": b"0",  # normal
            "1": b"3",  # portrait (90)
            "2": b"2",  # landscape (180)
            "3": b"1",  # portrait (270)
        }
        os.write_file("/sys/class/graphics/fbcon/rotate_all", fbcon_rotmap[rotation])


class LanguageSetting(StaticChoiceSetting):
    title = "Language"
    config_key = "core.language"
    priority = 70

    def __init__(self, shell: protocol.OpenVarioShell):
        self.shell = shell
        super().__init__()

    def read(self) -> Optional[str]:
        return self.shell.settings.get(self.config_key, str)

    def store(self, value: Optional[str]) -> None:
        self.shell.settings.set(self.config_key, value, save=True)

    def get_choices(self) -> Sequence[Tuple[str, str]]:
        return [
            ("en_EN.UTF-8", "English"),
            ("de_DE.UTF-8", "German"),
            ("fr_FR.UTF-8", "French"),
            ("ru_RU.UTF-8", "Russian"),
        ]


class ConsoleFontSetting(StaticChoiceSetting):
    title = "Font"
    priority = 50
    config_key = "core.font"

    def __init__(self, shell: protocol.OpenVarioShell):
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
    brightness_fname = "/sys/class/backlight/lcd/brightness"

    def __init__(self, shell: protocol.OpenVarioShell):
        self.shell = shell
        super().__init__()

    def read(self) -> Optional[str]:
        if not self.shell.os.file_exists(self.brightness_fname):
            return None
        br = self.shell.os.read_file(self.brightness_fname)
        return br.decode().strip()

    def store(self, value: Optional[str]) -> None:
        if value is None:
            return
        if not self.shell.os.file_exists(self.brightness_fname):
            return
        self.shell.os.write_file(self.brightness_fname, value.encode())

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


def apply_font(os: protocol.OpenVarioOS, font_name: str) -> None:
    setfont = os.host_path("/usr/bin/setfont")
    subprocess.run([setfont, font_name], check=True)
