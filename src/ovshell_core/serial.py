from typing import Sequence
from typing_extensions import Protocol
import asyncio

from serial.tools import list_ports

from ovshell import protocol


class SerialDeviceLookup(Protocol):
    def enumerate(self) -> Sequence[str]:
        pass


class SerialDeviceLookupImpl(SerialDeviceLookup):
    def enumerate(self) -> Sequence[str]:
        devs = list_ports.comports(include_links=False)
        return [d.device for d in devs]


async def maintain_serial_devices(
    shell: protocol.OpenVarioShell, devlookup: SerialDeviceLookup
) -> None:
    while True:
        devs = devlookup.enumerate()
        await asyncio.sleep(1)
