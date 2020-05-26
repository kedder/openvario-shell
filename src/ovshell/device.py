from typing import Optional, List, Dict
import asyncio

from ovshell import protocol


class DeviceUnavailable(Exception):
    def __init__(self, device):
        self.device = device


class DeviceManagerImpl(protocol.DeviceManager):
    _devices: Dict[str, protocol.Device]

    def __init__(self) -> None:
        self._devices = {}

    def register(self, device: protocol.Device) -> None:
        self._devices[device.id] = device

    def remove(self, devid: str) -> None:
        if devid in self._devices:
            del self._devices[devid]

    def list(self) -> List[protocol.Device]:
        return list(self._devices.values())

    def get(self, devid: str) -> Optional[protocol.Device]:
        return self._devices.get(devid)

    async def _read(self, dev: protocol.Device):
        try:
            return (dev, await dev.readline())
        except IOError as e:
            raise DeviceUnavailable(dev) from e

    async def read_devices(self) -> None:
        devmap = {}
        while True:
            for dev in self.list():
                if dev.id not in devmap:
                    devmap[dev.id] = self._read(dev)

            if not devmap:
                await asyncio.sleep(1)
                continue

            done, pending = await asyncio.wait(
                devmap.values(), timeout=1, return_when=asyncio.FIRST_COMPLETED
            )
            for task in done:
                try:
                    dev, msg = task.result()

                    print("RECV:", dev.id, msg)
                    devmap[dev.id] = self._read(dev)
                except DeviceUnavailable as e:
                    devid = e.device.id
                    print("REMOVING", devid)
                    del devmap[devid]
                    self.remove(devid)
