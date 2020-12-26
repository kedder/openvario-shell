import asyncio
import os
from typing import NoReturn, Set

import serial
from serial.tools.list_ports import comports
from serial_asyncio import open_serial_connection

from ovshell import api

DEVICE_OPEN_TIMEOUT = 1
DEVICE_POLL_TIMEOUT = 1
BAUD_DETECTION_INTERVAL = 0.2

# Built-in devices will not be detected by comports(), list those explicitly.
BUILTIN_DEVICES = ["//dev/ttyS1", "//dev/ttyS2", "//dev/ttyS3"]
STANDARD_BAUDRATES = [9600, 14400, 19200, 38400, 57600, 115200]


class DeviceOpenError(Exception):
    def __init__(self, path: str) -> None:
        self.path = path


class BaudRateNotDetected(DeviceOpenError):
    pass


class SerialDeviceImpl(api.SerialDevice):
    def __init__(
        self,
        dev_path: str,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
        baudrate: int,
    ) -> None:
        self.path = dev_path
        self.id = dev_path
        self.name = os.path.basename(dev_path)
        self.baudrate = baudrate
        self._reader = reader
        self._writer = writer

    @staticmethod
    async def open(dev_path: str) -> "SerialDeviceImpl":
        for baudrate in STANDARD_BAUDRATES:
            try:
                reader, writer = await open_serial_connection(
                    url=str(dev_path), baudrate=baudrate
                )
                data = await reader.readexactly(20)
            except serial.SerialException as e:
                raise DeviceOpenError(dev_path) from e

            if _is_ascii(data):
                return SerialDeviceImpl(dev_path, reader, writer, baudrate)
            else:
                writer.close()
                await writer.wait_closed()
                await asyncio.sleep(BAUD_DETECTION_INTERVAL)

        raise BaudRateNotDetected(dev_path)

    async def readline(self) -> bytes:
        return await self._reader.readline()

    def write(self, data: bytes) -> None:
        self._writer.write(data)


async def maintain_serial_devices(shell: api.OpenVarioShell) -> NoReturn:
    os_devs: Set[str]
    opening = {}
    builtins = [shell.os.path(dev) for dev in BUILTIN_DEVICES]
    while True:
        os_devs = set(d.device for d in comports(include_links=False))
        os_devs.update(d for d in builtins if os.path.exists(d))

        registered_devs = [
            d.path for d in shell.devices.list() if isinstance(d, SerialDeviceImpl)
        ]

        for dp in os_devs:
            if dp not in opening and dp not in registered_devs:
                opening[dp] = asyncio.create_task(SerialDeviceImpl.open(dp))

        if not opening:
            await asyncio.sleep(DEVICE_POLL_TIMEOUT)
            continue

        for task in asyncio.as_completed(opening.values(), timeout=DEVICE_OPEN_TIMEOUT):
            try:
                dev = await task
                del opening[str(dev.path)]
                shell.devices.register(dev)
            except asyncio.TimeoutError:
                break
            except DeviceOpenError as e:
                del opening[e.path]

        await asyncio.sleep(DEVICE_POLL_TIMEOUT)


def _is_ascii(data: bytes) -> bool:
    return all(10 <= b <= 127 for b in data)
