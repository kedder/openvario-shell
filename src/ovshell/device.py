from typing import Optional, List, Dict, Generator, Tuple, Set
import asyncio
from contextlib import contextmanager
from dataclasses import dataclass

from ovshell import protocol


class InvalidNMEA(ValueError):
    pass


@dataclass
class NMEA:
    device_id: str
    raw_message: str

    @staticmethod
    def parse(device_id: str, message: bytes) -> "NMEA":
        strmsg = message.decode().strip()
        if not is_nmea_valid(strmsg):
            raise InvalidNMEA()

        return NMEA(device_id=device_id, raw_message=strmsg)


class DeviceUnavailable(Exception):
    def __init__(self, device):
        self.device = device


def nmea_checksum(nmea_str: str) -> str:
    chksum = 0
    for c in nmea_str:
        chksum ^= ord(c)
    return f"{chksum:2X}"


def is_nmea_valid(nmea_msg: str) -> bool:
    if not nmea_msg.startswith("$"):
        return False
    parts = nmea_msg.rsplit("*", 1)
    if len(parts) != 2:
        return False
    body, chksum = parts
    return nmea_checksum(body[1:]) == chksum


def format_nmea(nmea_str: str) -> str:
    chksum = nmea_checksum(nmea_str)
    return f"${nmea_str}*{chksum}"


class NMEAStream:
    def __init__(self, queue: "asyncio.Queue[NMEA]") -> None:
        self._queue = queue

    async def read(self) -> NMEA:
        return await self._queue.get()

    def __aiter__(self):
        return self

    async def __anext__(self):
        return await self.read()


class DeviceManagerImpl(protocol.DeviceManager):
    _devices: Dict[str, protocol.Device]

    def __init__(self) -> None:
        self._devices = {}
        self._queues: "Set[asyncio.Queue[NMEA]]" = set()

    def register(self, device: protocol.Device) -> None:
        self._devices[device.id] = device

    def remove(self, devid: str) -> None:
        if devid in self._devices:
            del self._devices[devid]

    def list(self) -> List[protocol.Device]:
        return list(self._devices.values())

    def get(self, devid: str) -> Optional[protocol.Device]:
        return self._devices.get(devid)

    @contextmanager
    def open_nmea(self) -> Generator[NMEAStream, None, None]:
        q: "asyncio.Queue[NMEA]" = asyncio.Queue(maxsize=100)
        self._queues.add(q)
        yield NMEAStream(q)
        self._queues.remove(q)

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
                    self._publish(dev, msg)
                    devmap[dev.id] = self._read(dev)
                except DeviceUnavailable as e:
                    devid = e.device.id
                    del devmap[devid]
                    self.remove(devid)

    def _publish(self, dev: protocol.Device, msg: bytes) -> None:
        if not self._queues:
            return

        try:
            nmea = NMEA.parse(dev.id, msg)
        except InvalidNMEA:
            return

        for q in self._queues:
            if q.full():
                q.get_nowait()
            q.put_nowait(nmea)
