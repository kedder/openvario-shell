import os

from ovshell import protocol


class OpenVarioOSImpl(protocol.OpenVarioOS):
    _rootfs: str = "/"

    def __init__(self):
        pass

    def mount_boot(self) -> None:
        pass

    def unmount_boot(self) -> None:
        pass

    def read_file(self, filename: str) -> bytes:
        fpath = self._normalize_path(filename)
        with open(fpath, "rb") as f:
            return f.read()

    def write_file(self, filename: str, content: bytes) -> None:
        fpath = self._normalize_path(filename)
        with open(fpath, "wb") as f:
            f.write(content)

    def _normalize_path(self, fname: str) -> str:
        assert fname.startswith("/"), "Absolute path is required"
        return os.path.join(self._rootfs, fname[1:])


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
