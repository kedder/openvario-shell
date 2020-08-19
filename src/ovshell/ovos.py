from typing import List
import asyncio
import sys
import os
import subprocess

from ovshell import api


class OSProcessImpl(api.OSProcess):
    def __init__(self, proc: asyncio.subprocess.Process) -> None:
        self._process = proc

    async def wait(self) -> int:
        return await self._process.wait()

    async def read_stderr(self) -> bytes:
        assert self._process.stderr is not None
        return await self._process.stderr.read()


class OpenVarioOSImpl(api.OpenVarioOS):
    def mount_boot(self) -> None:
        subprocess.run(["mount", "/dev/mmcblk0p1", "/boot"], check=True)

    def unmount_boot(self) -> None:
        subprocess.run(["umount", "/boot"], check=True)

    def path(self, fname: str) -> str:
        assert fname.startswith("/"), "Absolute path is required"
        if fname.startswith("//"):
            return fname[1:]
        return fname

    async def run(self, command: str, args: List[str]) -> api.OSProcess:
        proc = await asyncio.create_subprocess_exec(
            self.path(command),
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            limit=200,
        )
        return OSProcessImpl(proc)

    def sync(self) -> None:
        os.sync()

    def shut_down(self) -> None:
        self.sync()
        subprocess.run(["halt"])

    def restart(self) -> None:
        subprocess.run(["reboot"])


class OpenVarioOSSimulator(OpenVarioOSImpl):
    def __init__(self, rootfs: str) -> None:
        super().__init__()
        self._rootfs = rootfs

    def mount_boot(self) -> None:
        fd = os.open(self._rootfs, os.O_RDONLY)
        os.symlink("boot.unmounted", "boot", dir_fd=fd)
        os.close(fd)

    def unmount_boot(self) -> None:
        mountpath = os.path.join(self._rootfs, "boot")
        os.unlink(mountpath)

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
