from typing import Sequence
from typing_extensions import Protocol
from pathlib import Path
import asyncio

from serial_asyncio import open_serial_connection
from serial.tools import list_ports

from ovshell import protocol


class SerialDeviceLookup(Protocol):
    def enumerate(self) -> Sequence[str]:
        pass


class SerialDeviceLookupImpl(SerialDeviceLookup):
    def enumerate(self) -> Sequence[str]:
        devs = list_ports.comports(include_links=False)
        return [d.device for d in devs]


class SerialDeviceImpl(protocol.SerialDevice):
    def __init__(self, dev_path: Path, reader, writer) -> None:
        self.path = dev_path
        self.id = str(dev_path)
        self.name = dev_path.name
        self._reader = reader
        self._writer = writer

    @staticmethod
    async def open(dev_path: Path) -> "SerialDeviceImpl":
        reader, writer = await open_serial_connection(
            url=str(dev_path), baudrate=115200
        )
        return SerialDeviceImpl(dev_path, reader, writer)

    async def read(self) -> bytes:
        return await self._reader.read()

    async def readline(self) -> bytes:
        return await self._reader.readline()

    def write(self, data: bytes) -> None:
        self._writer.write(data)


async def maintain_serial_devices(
    shell: protocol.OpenVarioShell, devlookup: SerialDeviceLookup
) -> None:
    while True:
        os_devs = set(devlookup.enumerate())
        shell_devs = [
            d for d in shell.devices.list() if isinstance(d, protocol.SerialDevice)
        ]
        shell_dev_idx = {d.id: d for d in shell_devs}

        new_devs = os_devs.difference(shell_dev_idx.keys())
        # remove_devs = set(shell_dev_idx.keys()).difference(os_devs)
        print("new_devs", new_devs)

        if not new_devs:
            await asyncio.sleep(1)
            continue

        devs = [SerialDeviceImpl.open(Path(dp)) for dp in new_devs]
        for pending_dev in asyncio.as_completed(devs, timeout=1):
            try:
                dev = await pending_dev
            except asyncio.TimeoutError:
                print("TIMEOUT HAPPENED")
            print("DEV OPENED, REGISTERING", dev)
            shell.devices.register(dev)

        # Install new devices
        await asyncio.sleep(1)
