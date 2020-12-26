import asyncio

import pytest

from ovshell import api, testing
from ovshell_core import devindicators


class SampleDevice(api.Device):
    def __init__(self, id: str, name: str) -> None:
        self.id = id
        self.name = name

    async def readline(self) -> bytes:
        return b""

    def write(self, data: bytes) -> None:
        pass


@pytest.mark.asyncio
async def test_nodevs(ovshell: testing.OpenVarioShellStub, monkeypatch) -> None:
    # GIVEN
    monkeypatch.setattr("ovshell_core.devindicators.DEVICE_POLL_INTERVAL", 0.01)

    # WHEN
    task = asyncio.create_task(devindicators.show_device_indicators(ovshell))
    await asyncio.sleep(0)

    # THEN
    assert ovshell.screen.stub_list_indicators() == []

    task.cancel()
    await asyncio.sleep(0)
    assert task.cancelled()


@pytest.mark.asyncio
async def test_dev_indicators(ovshell: testing.OpenVarioShellStub, monkeypatch) -> None:
    # GIVEN
    monkeypatch.setattr("ovshell_core.devindicators.DEVICE_POLL_INTERVAL", 0.01)
    dev = SampleDevice("sample", "Sample")
    ovshell.devices.register(dev)

    # WHEN
    task = asyncio.create_task(devindicators.show_device_indicators(ovshell))
    await asyncio.sleep(0)

    # THEN
    ind = ovshell.screen.stub_get_indicator("sample")
    assert ind is not None
    assert ind.location == api.IndicatorLocation.RIGHT

    task.cancel()
    await asyncio.sleep(0)
    assert task.cancelled()


@pytest.mark.asyncio
async def test_remove_indicators(
    ovshell: testing.OpenVarioShellStub, monkeypatch
) -> None:
    # GIVEN
    monkeypatch.setattr("ovshell_core.devindicators.DEVICE_POLL_INTERVAL", 0.01)
    ovshell.devices.register(SampleDevice("sample1", "Sample 1"))
    ovshell.devices.register(SampleDevice("sample2", "Sample 2"))

    task = asyncio.create_task(devindicators.show_device_indicators(ovshell))
    await asyncio.sleep(0)
    assert len(ovshell.screen.stub_list_indicators()) == 2

    # WHEN
    ovshell.devices.stub_remove_device("sample1")
    await asyncio.sleep(0.02)

    # THEN
    assert len(ovshell.screen.stub_list_indicators()) == 1
    ind = ovshell.screen.stub_get_indicator("sample")
    assert ind is None

    task.cancel()
    await asyncio.sleep(0)
    assert task.cancelled()
