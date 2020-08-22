from abc import abstractmethod
import asyncio
import os
import platform
import re
from typing import Dict, List, Optional, Tuple, cast

from ovshell import api


class SystemInfo:
    @abstractmethod
    async def get_openvario_version(self) -> Optional[str]:
        """Return Openvario image version"""

    @abstractmethod
    async def get_installed_package_version(self, package_name: str) -> Optional[str]:
        """Return version of installed opkg package"""

    @abstractmethod
    async def get_kernel_version(self) -> Optional[str]:
        """Return kernel version"""

    @abstractmethod
    async def get_hostname(self) -> Optional[str]:
        """Return hostname"""


class SystemInfoImpl(SystemInfo):
    _installed_pkgs: Optional[Dict[str, str]] = None

    def __init__(self, ovos: api.OpenVarioOS) -> None:
        self.os = ovos
        self._opkg_lock = asyncio.Lock()

    async def get_openvario_version(self) -> Optional[str]:
        release_fname = self.os.path("//etc/os-release")
        if not os.path.exists(release_fname):
            return None
        with open(release_fname, "r") as f:
            release = f.read()
        m = re.search(r"VERSION=\"(.*)\"", release)
        if m:
            return m.group(1)
        return None

    async def get_installed_package_version(self, package_name: str) -> Optional[str]:
        async with self._opkg_lock:
            if self._installed_pkgs is None:
                self._installed_pkgs = await self._read_installed_packages()
        return self._installed_pkgs.get(package_name)

    async def get_kernel_version(self) -> Optional[str]:
        uname = os.uname()
        return f"{uname.sysname} {uname.release}"

    async def get_hostname(self) -> Optional[str]:
        return os.uname().nodename

    async def _read_installed_packages(self) -> Dict[str, str]:
        proc = await self.os.run("//usr/bin/opkg", ["list-installed"])
        pkgs = []
        while not proc.stdout.at_eof():
            line = await proc.stdout.readline()
            sline = line.decode().strip()
            parts = sline.split(" - ")
            if len(parts) != 2:
                continue
            pkgs.append(cast(Tuple[str, str], tuple(parts)))

        return dict(pkgs)
