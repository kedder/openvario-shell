import asyncio
import os

from ovshell import api

SIM_READ_DELAY = 0.1


class SimulatedDeviceImpl(api.Device):
    def __init__(self, filename: str) -> None:
        self.id = "sim"
        self.name = os.path.basename(filename)
        self._filename = filename
        self._file = open(self._filename, "rb")

    async def readline(self) -> bytes:
        await asyncio.sleep(SIM_READ_DELAY)
        line = self._file.readline()
        if not line:
            # EOF
            self._file.seek(0)
            line = self._file.readline()
        return line

    def write(self, data: bytes) -> None:
        raise NotImplementedError()  # pragma: nocover


def run_simulated_device(shell: api.OpenVarioShell, filename: str) -> None:
    dev = SimulatedDeviceImpl(filename)
    shell.devices.register(dev)
