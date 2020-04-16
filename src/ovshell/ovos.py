import sys
import os
import subprocess

from ovshell import protocol


class OpenVarioOSImpl(protocol.OpenVarioOS):
    def mount_boot(self) -> None:
        subprocess.run(["mount", "/dev/mmcblk0p1", "/boot"], check=True)

    def unmount_boot(self) -> None:
        subprocess.run(["umount", "/boot"], check=True)

    def read_file(self, filename: str) -> bytes:
        fpath = self.host_path(filename)
        with open(fpath, "rb") as f:
            return f.read()

    def write_file(self, filename: str, content: bytes) -> None:
        fpath = self.host_path(filename)
        with open(fpath, "wb") as f:
            f.write(content)

    def file_exists(self, filename: str) -> bool:
        return os.path.exists(self.host_path(filename))

    def host_path(self, fname: str) -> str:
        assert fname.startswith("/"), "Absolute path is required"
        return fname

    def shut_down(self) -> None:
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

    def host_path(self, fname: str) -> str:
        fname = super().host_path(fname)
        return os.path.join(self._rootfs, fname[1:])

    def shut_down(self) -> None:
        print("Shut down requested")
        sys.exit(1)

    def restart(self) -> None:
        print("Restart requested")
        sys.exit(2)
