from typing import Union, Optional, List, Dict
from pathlib import Path
import asyncio
import weakref

from ovshell import protocol


class EOF:
    pass


NmeaStreamItem = Union[str, EOF]


class DeviceIOImpl(protocol.DeviceIO):
    def __init__(
        self, device: "SerialNmeaDevice", queue: "asyncio.Queue[NmeaStreamItem]"
    ):
        self._device = device
        self._queue = queue

    async def read(self) -> str:
        sentence = await self._queue.get()
        if isinstance(sentence, EOF):
            raise EOFError()
        return sentence

    def write(self, data: str) -> None:
        raise NotImplementedError()

    def close(self) -> None:
        self._device.close_nmea(self._queue)


class SerialNmeaDevice(protocol.Device, protocol.SerialDevice, protocol.NmeaDevice):
    _queues: "weakref.WeakSet[asyncio.Queue[NmeaStreamItem]]"

    def __init__(self, dev_path: Path) -> None:
        self.path = dev_path
        self.id = str(dev_path)
        self.name = dev_path.name
        self._queues = weakref.WeakSet()

    def open_nmea(self) -> protocol.DeviceIO:
        queue: asyncio.Queue[NmeaStreamItem] = asyncio.Queue(100)
        self._queues.add(queue)
        return DeviceIOImpl(self, queue)

    def close_nmea(self, queue: "asyncio.Queue[NmeaStreamItem]") -> None:
        self._queues.remove(queue)

    def _dispatch_nmea(self, sentence: NmeaStreamItem) -> None:
        for q in self._queues:
            if q.full():
                # Disacard latest item if queue is full
                q.get_nowait()
            q.put_nowait(sentence)

    def _close(self) -> None:
        self._dispatch_nmea(EOF())


class DeviceManagerImpl(protocol.DeviceManager):
    _devices: Dict[str, protocol.Device]

    def __init__(self) -> None:
        self._devices = {}

    def register(self, device: protocol.Device) -> None:
        self._devices[device.id] = device
        pass

    def remove(self, devid: str) -> None:
        if devid in self._devices:
            del self._devices[devid]

    def list(self) -> List[protocol.Device]:
        return list(self._devices.values())

    def get(self, devid: str) -> Optional[protocol.Device]:
        return self._devices.get(devid)
