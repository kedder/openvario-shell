from abc import abstractmethod
from dataclasses import dataclass
from typing import List

from ovshell.api import OpenVarioOS


@dataclass
class UpgradablePackage:
    name: str
    old_version: str
    new_version: str


@dataclass
class InstalledPackage:
    name: str
    version: str


class OpkgTools:
    @abstractmethod
    async def list_upgradables(self) -> List[UpgradablePackage]:
        """Return list of upgradable packages"""

    @abstractmethod
    async def list_installed(self) -> List[InstalledPackage]:
        """Return list of all installed packages"""

    @abstractmethod
    def get_opkg_binary(self) -> str:
        """Return the absolute path to opkg binary"""


class OpkgToolsImpl(OpkgTools):
    def __init__(self, ovos: OpenVarioOS, opkg_binary: str):
        self.ovos = ovos
        self.opkg_binary = opkg_binary

    async def list_upgradables(self) -> List[UpgradablePackage]:
        proc = await self.ovos.run(self.opkg_binary, ["list-upgradable"])
        upgradables = []
        while not proc.stdout.at_eof():
            bline = await proc.stdout.readline()

            line = bline.decode().strip()
            items = line.split(" - ")
            if len(items) != 3:
                # Bad format
                continue
            pkgname, old_version, new_version = items
            upgradables.append(UpgradablePackage(pkgname, old_version, new_version))

        returncode = await proc.wait()
        if returncode != 0:
            return []

        return upgradables

    async def list_installed(self) -> List[InstalledPackage]:
        proc = await self.ovos.run(self.opkg_binary, ["list-installed"])
        pkgs = []
        while not proc.stdout.at_eof():
            line = await proc.stdout.readline()
            sline = line.decode().strip()
            parts = sline.split(" - ")
            if len(parts) != 2:
                continue
            pkgs.append(InstalledPackage(name=parts[0], version=parts[1]))

        return pkgs

    def get_opkg_binary(self) -> str:
        return self.ovos.path(self.opkg_binary)


def create_opkg_tools(ovos: OpenVarioOS) -> OpkgTools:
    return OpkgToolsImpl(ovos, "//usr/bin/opkg")
