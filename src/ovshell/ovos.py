import asyncio
import os
import subprocess
import sys
from typing import Optional

from dbus_next.aio import MessageBus
from dbus_next.auth import AuthAnnonymous
from dbus_next.constants import BusType
from dbus_next.errors import AuthError, InvalidAddressError

from ovshell import api


class OSProcessImpl(api.OSProcess):
    def __init__(self, proc: asyncio.subprocess.Process) -> None:
        self._process = proc
        assert proc.stdout is not None
        self.stdout = proc.stdout
        assert proc.stderr is not None
        self.stderr = proc.stderr

    async def wait(self) -> int:
        return await self._process.wait()

    async def read_stderr(self) -> bytes:
        assert self._process.stderr is not None
        return await self._process.stderr.read()


class OpenVarioOSImpl(api.OpenVarioOS):
    _dbus: Optional[MessageBus] = None

    def __init__(self) -> None:
        self._dbus_connect_lock = asyncio.Lock()

    def path(self, fname: str) -> str:
        assert fname.startswith("/"), "Absolute path is required"
        if fname.startswith("//"):
            return fname[1:]
        return fname

    async def run(self, command: str, args: list[str]) -> api.OSProcess:
        proc = await asyncio.create_subprocess_exec(
            self.path(command),
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            limit=200,
        )
        return OSProcessImpl(proc)

    async def get_system_bus(self) -> api.AbstractMessageBus:
        if self._dbus is not None:
            return self._dbus

        async with self._dbus_connect_lock:
            try:
                try:
                    bus = await MessageBus(bus_type=BusType.SYSTEM).connect()
                except AuthError:
                    # Fallback to anonymous connection
                    bus = await MessageBus(
                        bus_type=BusType.SYSTEM, auth=AuthAnnonymous()
                    ).connect()
            except (InvalidAddressError, OSError) as e:
                raise api.DBusNotAvailableException() from e
            self._dbus = bus

        return bus

    def sync(self) -> None:
        os.sync()

    def shut_down(self) -> None:
        self.sync()
        subprocess.run(["systemctl", "poweroff"])

    def restart(self) -> None:
        subprocess.run(["systemctl", "reboot"])

    def spawn_shell(self) -> None:
        subprocess.run(["clear"])
        print("Type 'exit' or press Ctrl-D to return to menu.")
        subprocess.run(["bash", "-l"])


class OpenVarioOSSimulator(OpenVarioOSImpl):
    def __init__(self, rootfs: str) -> None:
        super().__init__()
        self._rootfs = rootfs

    def path(self, fname: str) -> str:
        assert fname.startswith("/"), "Absolute path is required"
        if not fname.startswith("//"):
            return fname

        return os.path.join(self._rootfs, fname[2:])

    def shut_down(self) -> None:
        print("Shut down requested")
        sys.exit(1)

    def restart(self) -> None:
        print("Restart requested")
        sys.exit(2)
