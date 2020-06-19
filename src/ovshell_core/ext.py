from typing import Sequence
import os

from ovshell import protocol

from ovshell_core import settings
from ovshell_core import serial
from ovshell_core import gpstime
from ovshell_core import upgradeapp
from ovshell_core import devsim
from ovshell_core import devindicators


class CoreExtension(protocol.Extension):
    title = "Core"

    def __init__(self, id: str, shell: protocol.OpenVarioShell):
        self.id = id
        self.shell = shell
        self._init_settings()
        self._apply_font()

    def list_settings(self) -> Sequence[protocol.Setting]:
        return [
            settings.RotationSetting(self.shell),
            settings.LanguageSetting(self.shell),
            settings.ScreenBrightnessSetting(self.shell),
            settings.ConsoleFontSetting(self.shell),
            settings.AutostartAppSetting(self.shell),
            settings.AutostartTimeoutSetting(self.shell),
        ]

    def list_apps(self) -> Sequence[protocol.App]:
        return [upgradeapp.SystemUpgradeApp(self.shell)]

    def start(self) -> None:
        self.shell.processes.start(serial.maintain_serial_devices(self.shell))

        gpsstate = gpstime.GPSTimeState()
        self.shell.processes.start(gpstime.gps_time_sync(self.shell, gpsstate))
        self.shell.processes.start(gpstime.clock_indicator(self.shell.screen, gpsstate))

        simfile = os.environ.get("OVSHELL_CORE_SIMULATE_DEVICE")
        if simfile:
            devsim.run_simulated_device(self.shell, simfile)

        self.shell.processes.start(devindicators.show_device_indicators(self.shell))

    def _init_settings(self) -> None:
        config = self.shell.settings
        config.setdefault("core.screen_orientation", "0")
        config.setdefault("core.language", "en_EN.UTF-8")

    def _apply_font(self) -> None:
        config = self.shell.settings
        font = config.get("core.font", str)
        if font is not None:
            settings.apply_font(self.shell.os, font)
