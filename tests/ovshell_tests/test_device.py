import asyncio
from typing import List

import pytest

from ovshell import api, device
from ovshell.device import format_nmea, is_nmea_valid, nmea_checksum, parse_nmea


class DeviceStub(api.Device):
    id: str
    name: str
    _stream: List[bytes]
    _delay: float = 0

    def __init__(self, id: str, name: str) -> None:
        self.id = id
        self.name = name
        self._stream = []

    async def readline(self) -> bytes:
        if not self._stream:
            raise IOError()
        await asyncio.sleep(self._delay)
        return self._stream.pop() + b"\r\n"

    def write(self, data: bytes) -> None:
        pass

    def stub_set_stream(self, values: List[bytes]) -> None:
        self._stream = list(reversed(values))

    def stub_set_delay(self, delay: float) -> None:
        self._delay = delay


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


def test_parse_nmea() -> None:
    nmea = parse_nmea("devid", b"$PGRMZ,+51.1,m,3*10\r\n")
    assert nmea.device_id == "devid"
    assert nmea.raw_message == "$PGRMZ,+51.1,m,3*10"
    assert nmea.datatype == "PGRMZ"
    assert nmea.fields == ["+51.1", "m", "3"]


def test_DeviceManagerImpl_open_nmea_empty() -> None:
    # GIVEN
    devman = device.DeviceManagerImpl()

    # WHEN
    with devman.open_nmea() as nmea:
        # THEN
        assert nmea is not None


@pytest.mark.asyncio
async def test_DeviceManagerImpl_get() -> None:
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
    with devman.open_nmea() as nmea_stream:
        # THEN
        nmea = await nmea_stream.read()

    assert nmea.device_id == "one"
    assert nmea.raw_message == "$PGRMZ,+51.1,m,3*10"


@pytest.mark.asyncio
async def test_DeviceManagerImpl_multidevice(task_running) -> None:
    # GIVEN
    devman = device.DeviceManagerImpl()
    dev1 = DeviceStub("one", "One")
    dev1.stub_set_stream([b"$PGRMZ,+51.1,m,3*10"] * 3)
    dev1.stub_set_delay(0.1)
    devman.register(dev1)
    dev2 = DeviceStub("two", "TWO")
    dev2.stub_set_stream([b"$PFLAU,0,0,0,1,0,,0,,,*4F"] * 3)
    dev2.stub_set_delay(0.25)
    devman.register(dev2)

    # WHEN
    with devman.open_nmea() as nmea_stream:
        # THEN
        nmea1 = await nmea_stream.read()
        nmea2 = await nmea_stream.read()
        nmea3 = await nmea_stream.read()

    assert nmea1.device_id == "one"
    assert nmea1.raw_message == "$PGRMZ,+51.1,m,3*10"
    assert nmea2.device_id == "one"
    assert nmea2.raw_message == "$PGRMZ,+51.1,m,3*10"

    assert nmea3.device_id == "two"
    assert nmea3.raw_message == "$PFLAU,0,0,0,1,0,,0,,,*4F"


@pytest.mark.asyncio
async def test_DeviceManagerImpl_remove_device_on_error(task_running) -> None:
    # GIVEN
    devman = device.DeviceManagerImpl()
    dev = DeviceStub("one", "One")
    devman.register(dev)
    assert len(devman.list()) == 1

    # WHEN
    with devman.open_nmea() as nmea_stream:
        # THEN
        read = nmea_stream.read()
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(read, timeout=0.01)

    assert len(devman.list()) == 0


@pytest.mark.asyncio
async def test_DeviceManagerImpl_remove_on_binary() -> None:
    # When non-ascii is received on device, drop it and try to reconnect again
    devman = device.DeviceManagerImpl()
    dev = DeviceStub("one", "One")
    dev.stub_set_stream([b"GOOD ASCII", b"\xFF"])
    dev.stub_set_delay(0.01)
    devman.register(dev)

    with devman.open_nmea() as nmea_stream:
        # THEN
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(nmea_stream.read(), timeout=0.05)

    assert len(devman.list()) == 0


@pytest.mark.asyncio
async def test_DeviceManagerImpl_bad_nmea() -> None:
    # GIVEN
    devman = device.DeviceManagerImpl()
    dev = DeviceStub("one", "One")
    dev.stub_set_stream([b"$BAD,nmea", b"$PGRMZ,+51.1,m,3*10"])
    devman.register(dev)

    # WHEN
    with devman.open_nmea() as nmea_stream:
        # THEN
        async for nmea in nmea_stream:
            break  # read only one message

    assert nmea.device_id == "one"
    assert nmea.raw_message == "$PGRMZ,+51.1,m,3*10"
