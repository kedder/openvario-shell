from typing import NoReturn
from pathlib import Path
import asyncio

import serial
from serial_asyncio import open_serial_connection
from serial.tools.list_ports import comports

from ovshell import protocol

DEVICE_OPEN_TIMEOUT = 1
DEVICE_POLL_TIMEOUT = 1


class SerialDeviceImpl(protocol.SerialDevice):
    def __init__(
        self,
        dev_path: Path,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
        baudrate: int,
    ) -> None:
        self.path = dev_path
        self.id = str(dev_path)
        self.name = dev_path.name
        self.baudrate = baudrate
        self._reader = reader
        self._writer = writer

    @staticmethod
    async def open(dev_path: Path) -> "SerialDeviceImpl":
        baudrate = 115200
        reader, writer = await open_serial_connection(
            url=str(dev_path), baudrate=baudrate
        )
        return SerialDeviceImpl(dev_path, reader, writer, baudrate)

    async def read(self) -> bytes:
        return await self._reader.read()

    async def readline(self) -> bytes:
        return await self._reader.readline()

    def write(self, data: bytes) -> None:
        self._writer.write(data)


async def maintain_serial_devices(shell: protocol.OpenVarioShell) -> NoReturn:
    while True:
        os_devs = set(d.device for d in comports(include_links=False))

        shell_devs = [
            d for d in shell.devices.list() if isinstance(d, SerialDeviceImpl)
        ]
        shell_dev_idx = {d.id: d for d in shell_devs}
        new_devs = os_devs.difference(shell_dev_idx.keys())

        if not new_devs:
            await asyncio.sleep(DEVICE_POLL_TIMEOUT)
            continue

        devs = [SerialDeviceImpl.open(Path(dp)) for dp in new_devs]
        for pending_dev in asyncio.as_completed(devs, timeout=DEVICE_OPEN_TIMEOUT):
            try:
                dev = await pending_dev
            except asyncio.TimeoutError:
                break
            except serial.SerialException:
                continue
            shell.devices.register(dev)

        await asyncio.sleep(DEVICE_POLL_TIMEOUT)
