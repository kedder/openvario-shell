import os
from typing import Sequence

from ovshell import api
from ovshell_core import aboutapp, devindicators, devsim, gpstime, serial, settings
from ovshell_core import setupapp, upgradeapp


class CoreExtension(api.Extension):
    title = "Core"

    def __init__(self, id: str, shell: api.OpenVarioShell):
        self.id = id
        self.shell = shell
        self._init_settings()
        self._apply_font()

    def list_settings(self) -> Sequence[api.Setting]:
        return [
            settings.RotationSetting(self.shell),
            settings.LanguageSetting(self.shell),
            settings.ScreenBrightnessSetting(self.shell),
            settings.ConsoleFontSetting(self.shell),
            settings.AutostartAppSetting(self.shell),
            settings.AutostartTimeoutSetting(self.shell),
        ]

    def list_apps(self) -> Sequence[api.App]:
        return [
            upgradeapp.SystemUpgradeApp(self.shell),
            setupapp.SetupApp(self.shell, self.id),
            aboutapp.AboutApp(self.shell),
        ]

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
