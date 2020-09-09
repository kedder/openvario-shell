from typing import List
from abc import abstractmethod
from dataclasses import dataclass
import subprocess


@dataclass
class UpgradablePackage:
    name: str
    old_version: str
    new_version: str


class OpkgTools:
    opkg_binary: str

    @abstractmethod
    def list_upgradables(self) -> List[UpgradablePackage]:
        """Return list of upgradable packages"""


class OpkgToolsImpl(OpkgTools):
    def __init__(self, opkg_binary: str):
        self.opkg_binary = opkg_binary

    def list_upgradables(self) -> List[UpgradablePackage]:
        proc = subprocess.run(
            [self.opkg_binary, "list-upgradable"], capture_output=True
        )
        if proc.returncode != 0:
            return []

        blines = proc.stdout.split(b"\n")
        upgradables = []
        for bline in blines:
            line = bline.decode().strip()
            items = line.split(" - ")
            if len(items) != 3:
                # Bad format
                continue
            pkgname, old_version, new_version = items
            upgradables.append(UpgradablePackage(pkgname, old_version, new_version))
        return upgradables
