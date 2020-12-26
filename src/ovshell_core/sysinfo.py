import asyncio
import os
import re
from abc import abstractmethod
from typing import Dict, Optional

from ovshell import api

from .opkg import OpkgTools


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

    def __init__(self, ovos: api.OpenVarioOS, opkgtools: OpkgTools) -> None:
        self.os = ovos
        self.opkgtools = opkgtools
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
                installed = await self.opkgtools.list_installed()
                self._installed_pkgs = {p.name: p.version for p in installed}
        return self._installed_pkgs.get(package_name)

    async def get_kernel_version(self) -> Optional[str]:
        uname = os.uname()
        return f"{uname.sysname} {uname.release}"

    async def get_hostname(self) -> Optional[str]:
        return os.uname().nodename
