import asyncio
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import AsyncIterator, Coroutine, List, Optional, Tuple

import mock
import pytest
from serial import SerialException

from ovshell import testing
from ovshell_core import serial


class SerialDeviceLookupStub:
    _devices: List[str]

    def __init__(self) -> None:
        self._devices = []

    def stub_set_devices(self, devices: List[str]) -> None:
        self._devices = devices

    def comports(self, include_links: bool) -> List:
        return [mock.Mock(device=dev) for dev in self._devices]


class SerialConnecitionOpenerStub:
    open_raises: Optional[Exception] = None

    def __init__(self) -> None:
        self.reader = mock.Mock(asyncio.StreamReader)
        self.writer = mock.Mock(asyncio.StreamWriter)

    async def open_serial_connection(
        self, url: str, baudrate: int
    ) -> Tuple[asyncio.StreamReader, asyncio.StreamWriter]:
        if self.open_raises is not None:
            raise self.open_raises
        return self.reader, self.writer


@dataclass
class SerialTestbed:
    lookup: SerialDeviceLookupStub
    serial_opener: SerialConnecitionOpenerStub


@pytest.fixture
def serial_testbed(monkeypatch) -> SerialTestbed:
    lookup = SerialDeviceLookupStub()
    serial_opener = SerialConnecitionOpenerStub()

    # We cannot have timeouts of exactly 0, because we would make too many
    # iterations in our infinite loops in poller tasks.
    monkeypatch.setattr("ovshell_core.serial.DEVICE_POLL_TIMEOUT", 0.01)
    monkeypatch.setattr("ovshell_core.serial.DEVICE_OPEN_TIMEOUT", 0.01)
    monkeypatch.setattr("ovshell_core.serial.BAUD_DETECTION_INTERVAL", 0)
    monkeypatch.setattr(
        "ovshell_core.serial.open_serial_connection",
        serial_opener.open_serial_connection,
    )
    monkeypatch.setattr("ovshell_core.serial.comports", lookup.comports)

    return SerialTestbed(lookup, serial_opener)


@asynccontextmanager
async def task_started(coro: Coroutine) -> AsyncIterator:
    task = asyncio.create_task(coro)
    try:
        yield
    finally:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


@pytest.mark.asyncio
async def test_maintain_serial_devices_no_devs(
    ovshell: testing.OpenVarioShellStub, serial_testbed: SerialTestbed
) -> None:
    # GIVEN
    maintainer = serial.maintain_serial_devices(ovshell)
    async with task_started(maintainer):
        # WHEN
        await asyncio.sleep(0)

    # THEN
    # No devices registered
    assert len(ovshell.devices.list()) == 0


@pytest.mark.asyncio
async def test_maintain_serial_devices_bad_device(
    ovshell: testing.OpenVarioShellStub, serial_testbed: SerialTestbed
) -> None:
    # GIVEN
    serial_testbed.lookup.stub_set_devices(["/dev/ttyFAKE"])
    serial_testbed.serial_opener.open_raises = SerialException("File not found")
    maintainer = serial.maintain_serial_devices(ovshell)
    async with task_started(maintainer):
        # WHEN
        await asyncio.sleep(0.01)

    # THEN
    # No devices registered
    assert len(ovshell.devices.list()) == 0


@pytest.mark.asyncio
async def test_maintain_serial_devices_reconnect(
    ovshell: testing.OpenVarioShellStub, serial_testbed: SerialTestbed
) -> None:
    serial_testbed.lookup.stub_set_devices(["/dev/ttyFAKE"])
    maintainer = serial.maintain_serial_devices(ovshell)
    async with task_started(maintainer):
        # Device is detected
        await asyncio.sleep(0.02)
        assert len(ovshell.devices.list()) == 1

        # ttyFAKE is gone
        ovshell.devices.stub_remove_device("/dev/ttyFAKE")
        assert len(ovshell.devices.list()) == 0
        serial_testbed.lookup.stub_set_devices([])
        await asyncio.sleep(0.02)

        # ttyFAKE reappears
        serial_testbed.lookup.stub_set_devices(["/dev/ttyFAKE"])
        await asyncio.sleep(0.02)
        assert len(ovshell.devices.list()) == 1


@pytest.mark.asyncio
async def test_maintain_serial_devices_opened(
    ovshell: testing.OpenVarioShellStub, serial_testbed: SerialTestbed
) -> None:

    serial_testbed.lookup.stub_set_devices(["/dev/ttyFAKE"])
    maintainer = serial.maintain_serial_devices(ovshell)
    async with task_started(maintainer):
        # WHEN
        await asyncio.sleep(0.01)

    # THEN
    # One device registered
    devs = ovshell.devices.list()
    assert len(devs) == 1
    dev = devs[0]
    assert isinstance(dev, serial.SerialDeviceImpl)
    assert dev.id == "/dev/ttyFAKE"
    assert dev.name == "ttyFAKE"
    assert dev.path == "/dev/ttyFAKE"
    assert dev.baudrate == 9600


@pytest.mark.asyncio
async def test_SerialDeviceImpl_baud_autodetect(serial_testbed: SerialTestbed) -> None:
    # GIVEN
    serial_testbed.serial_opener.reader.readexactly.side_effect = [
        b"\0" * 20,
        b"\xff" * 20,
        b"X" * 20,
    ]
    serial_testbed.serial_opener.reader.read.return_value = b"hello"

    # WHEN
    dev = await serial.SerialDeviceImpl.open("/dev/ttyFAKE")

    # THEN
    assert dev.baudrate == 19200


@pytest.mark.asyncio
async def test_SerialDeviceImpl_baud_notdetected(serial_testbed: SerialTestbed) -> None:
    # GIVEN
    serial_testbed.serial_opener.reader.readexactly.side_effect = [
        b"\0" * 20,
        b"\xff" * 20,
        b"\x01" * 20,
        b"\x02" * 20,
        b"\x03" * 20,
        b"\x04" * 20,
        b"\x05" * 20,
    ]
    serial_testbed.serial_opener.reader.read.return_value = b"hello"

    # WHEN
    with pytest.raises(serial.BaudRateNotDetected):
        await serial.SerialDeviceImpl.open("/dev/ttyFAKE")


@pytest.mark.asyncio
async def test_SerialDeviceImpl_readline(serial_testbed: SerialTestbed) -> None:
    # GIVEN
    dev = await serial.SerialDeviceImpl.open("/dev/ttyFAKE")
    serial_testbed.serial_opener.reader.readline.return_value = b"hello\r\n"

    # WHEN
    data = await dev.readline()

    # THEN
    assert data == b"hello\r\n"


@pytest.mark.asyncio
async def test_SerialDeviceImpl_write(serial_testbed: SerialTestbed) -> None:
    # GIVEN
    dev = await serial.SerialDeviceImpl.open("/dev/ttyFAKE")

    # WHEN
    dev.write(b"hello")

    # THEN
    assert serial_testbed.serial_opener.writer.write.called_with(b"hello")
