from typing import Union
from typing_extensions import Protocol
from abc import abstractmethod
import asyncio
import weakref
from pathlib import Path


class Device(Protocol):
    id: str
    name: str


class DeviceIO(Protocol):
    @abstractmethod
    async def read(self) -> str:
        pass

    @abstractmethod
    def write(self, data: str) -> None:
        pass


class NmeaDevice(Protocol):
    @abstractmethod
    def open_nmea(self) -> DeviceIO:
        pass


class SerialDevice(Protocol):
    baud_rate: int
    path: Path


class EOF:
    pass


NmeaStreamItem = Union[str, EOF]


class DeviceIOImpl(DeviceIO):
    def __init__(
        self, device: "SerialNmeaDevice", queue: asyncio.Queue[NmeaStreamItem]
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


class SerialNmeaDevice(Device, SerialDevice, NmeaDevice):
    _queues: weakref.WeakSet[asyncio.Queue[NmeaStreamItem]]

    def __init__(self, dev_path: Path) -> None:
        self.path = dev_path
        self.id = str(dev_path)
        self.name = dev_path.name
        self._queues = weakref.WeakSet()

    def open_nmea(self) -> DeviceIO:
        queue: asyncio.Queue[NmeaStreamItem] = asyncio.Queue(100)
        self._queues.add(queue)
        return DeviceIOImpl(self, queue)

    def close_nmea(self, queue: asyncio.Queue[NmeaStreamItem]) -> None:
        self._queues.remove(queue)

    def _dispatch_nmea(self, sentence: NmeaStreamItem) -> None:
        for q in self._queues:
            if q.full():
                # Disacard latest item if queue is full
                q.get_nowait()
            q.put_nowait(sentence)

    def _close(self) -> None:
        self._dispatch_nmea(EOF())
