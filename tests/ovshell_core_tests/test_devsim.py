import os

import pytest

from ovshell import testing
from ovshell_core import devsim

HERE = os.path.dirname(__file__)


@pytest.mark.asyncio
async def test_run_simulated_device(ovshell: testing.OpenVarioShellStub) -> None:
    # GIVEN
    samplefile = os.path.join(HERE, "samples", "sample.nmea")

    # WHEN
    devsim.run_simulated_device(ovshell, samplefile)

    # THEN
    devs = ovshell.devices.list()
    assert len(devs) == 1
    assert isinstance(devs[0], devsim.SimulatedDeviceImpl)


@pytest.mark.asyncio
async def test_SimulatedDeviceImpl_readline_infinite(
    ovshell: testing.OpenVarioShellStub, monkeypatch
) -> None:
    # GIVEN
    samplefile = os.path.join(HERE, "samples", "sample.nmea")
    monkeypatch.setattr("ovshell_core.devsim.SIM_READ_DELAY", 0)
    dev = devsim.SimulatedDeviceImpl(samplefile)

    # WHEN

    # There are only two lines in the file. When we read past the last line, we
    # start with the first one again.
    line1 = await dev.readline()
    line2 = await dev.readline()
    line3 = await dev.readline()

    # THEN
    assert line1.startswith(b"$POV")
    assert line2.startswith(b"$GPRMC")
    assert line1 == line3
