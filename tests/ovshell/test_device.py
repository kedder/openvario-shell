from typing import List

import asyncio
import pytest

from ovshell import device
from ovshell import protocol
from ovshell.device import nmea_checksum, format_nmea, is_nmea_valid


class DeviceStub(protocol.Device):
    id: str
    name: str
    _stream: List[bytes]

    def __init__(self, id: str, name: str) -> None:
        self.id = id
        self.name = name
        self._stream = []

    async def read(self) -> bytes:
        if not self._stream:
            raise IOError()
        return self._stream.pop()

    async def readline(self) -> bytes:
        if not self._stream:
            raise IOError()
        return self._stream.pop() + b"\r\n"

    def write(self, data: bytes) -> None:
        pass

    def stub_set_stream(self, values: List[bytes]) -> None:
        self._stream = list(reversed(values))


def test_nmea_checksum() -> None:
    assert nmea_checksum("PGRMZ,+51.1,m,3") == "10"
    assert nmea_checksum("PFLAU,0,0,0,1,0,,0,,,") == "4F"


def test_format_nmea() -> None:
    assert format_nmea("PGRMZ,+51.1,m,3") == "$PGRMZ,+51.1,m,3*10"
    assert format_nmea("PFLAU,0,0,0,1,0,,0,,,") == "$PFLAU,0,0,0,1,0,,0,,,*4F"


def test_is_nmea_valid() -> None:
    assert is_nmea_valid("$PGRMZ,+51.1,m,3*10")
    assert not is_nmea_valid("PGRMZ,+51.1,m,3*10")
    assert not is_nmea_valid("$PGRMZ,+51.1,m,3")
    assert not is_nmea_valid("$PGRMZ,+51.1,m,3*11")


def test_DeviceManagerImpl_open_nmea_empty() -> None:
    # GIVEN
    devman = device.DeviceManagerImpl()

    # WHEN
    with devman.open_nmea() as nmea:
        # THEN
        assert nmea is not None


def test_DeviceManagerImpl_get() -> None:
    # GIVEN
    devman = device.DeviceManagerImpl()
    dev = DeviceStub("one", "One")
    dev.stub_set_stream([b"$PGRMZ,+51.1,m,3*10"])
    devman.register(dev)

    # WHEN, THEN
    assert devman.get("one") == dev
    assert devman.get("two") is None


@pytest.mark.asyncio
async def test_DeviceManagerImpl_open_nmea_stream(task_running) -> None:
    # GIVEN
    devman = device.DeviceManagerImpl()
    dev = DeviceStub("one", "One")
    dev.stub_set_stream([b"$PGRMZ,+51.1,m,3*10"])
    devman.register(dev)

    # WHEN
    async with task_running(devman.read_devices()):
        with devman.open_nmea() as nmea_stream:
            # THEN
            nmea = await nmea_stream.read()

    assert nmea.device_id == "one"
    assert nmea.raw_message == "$PGRMZ,+51.1,m,3*10"


@pytest.mark.asyncio
async def test_DeviceManagerImpl_remove_device_on_error(task_running) -> None:
    # GIVEN
    devman = device.DeviceManagerImpl()
    dev = DeviceStub("one", "One")
    devman.register(dev)
    assert len(devman.list()) == 1

    # WHEN
    async with task_running(devman.read_devices()):
        with devman.open_nmea() as nmea_stream:
            # THEN
            read = nmea_stream.read()
            with pytest.raises(asyncio.TimeoutError):
                await asyncio.wait_for(read, timeout=0.01)

    assert len(devman.list()) == 0


@pytest.mark.asyncio
async def test_DeviceManagerImpl_bad_nmea(task_running) -> None:
    # GIVEN
    devman = device.DeviceManagerImpl()
    dev = DeviceStub("one", "One")
    dev.stub_set_stream([b"$BAD,nmea", b"$PGRMZ,+51.1,m,3*10"])
    devman.register(dev)

    # WHEN
    async with task_running(devman.read_devices()):
        with devman.open_nmea() as nmea_stream:
            # THEN
            async for nmea in nmea_stream:
                break  # read only one message

    assert nmea.device_id == "one"
    assert nmea.raw_message == "$PGRMZ,+51.1,m,3*10"
