import asyncio
from typing import Set

from ovshell import api

DEVICE_POLL_INTERVAL = 1


async def show_device_indicators(shell: api.OpenVarioShell) -> None:
    indicators: Set[str] = set()
    screen = shell.screen

    while True:
        devs = shell.devices.list()
        # Update existing indicators
        cur_indicators = set()
        for dev in devs:
            screen.set_indicator(dev.id, dev.name, api.IndicatorLocation.RIGHT, 0)
            cur_indicators.add(dev.id)

        # Clear indicators for removed devices
        removed = indicators - cur_indicators
        for indid in removed:
            screen.remove_indicator(indid)

        indicators = cur_indicators

        await asyncio.sleep(DEVICE_POLL_INTERVAL)
