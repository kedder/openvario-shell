from typing import Iterable, List, Optional, Set, cast

import pkg_resources
import urwid

from ovshell import api, device, ovos, process, settings
from ovshell.api import Extension, ExtensionFactory, OpenVarioShell, ScreenManager


class ExtensionManagerImpl(api.ExtensionManager):
    _extensions: List[Extension]

    def __init__(self):
        self._extensions = []

    def load_all(self, shell: OpenVarioShell) -> None:
        for entry_point in pkg_resources.iter_entry_points("ovshell.extensions"):
            extfactory = cast(ExtensionFactory, entry_point.load())
            ext = extfactory(entry_point.name, shell)
            self._extensions.append(ext)
            print(f"Loaded extension: {ext.title}")

    def list_extensions(self) -> Iterable[Extension]:
        return self._extensions


class AppManagerImpl(api.AppManager):
    def __init__(self, shell: OpenVarioShell) -> None:
        self.shell = shell

    def list(self) -> Iterable[api.AppInfo]:
        appinfos = []
        allpinned = self._get_pinned()
        for ext in self.shell.extensions.list_extensions():
            for app in ext.list_apps():
                appid = f"{ext.id}.{app.name}"
                appinfo = api.AppInfo(
                    id=appid, app=app, extension=ext, pinned=appid in allpinned,
                )
                appinfos.append(appinfo)

        appinfos = sorted(appinfos, key=lambda v: (-v.app.priority, v.extension.id))
        return appinfos

    def get(self, id: str) -> Optional[api.AppInfo]:
        for appinfo in self.list():
            if appinfo.id == id:
                return appinfo
        return None

    def pin(self, app: api.AppInfo, persist: bool = False) -> None:
        pinned = self._get_pinned()
        if app.id in pinned:
            return
        pinned.add(app.id)
        self._set_pinned(pinned, persist)

    def unpin(self, app: api.AppInfo, persist: bool = False) -> None:
        pinned = self._get_pinned()
        if app.id not in pinned:
            return
        pinned.remove(app.id)
        self._set_pinned(pinned, persist)

    def install_new_apps(self) -> List[api.AppInfo]:
        installed = self.shell.settings.get("ovshell.installed_apps", list) or []
        newapps = []
        for appinfo in self.list():
            if appinfo.id in installed:
                continue

            print(f"Installing new app {appinfo.id}")
            appinfo.app.install(appinfo)
            installed.append(appinfo.id)
            newapps.append(appinfo)

        if newapps:
            self.shell.settings.set("ovshell.installed_apps", sorted(installed), True)

        return newapps

    def _get_pinned(self) -> Set[str]:
        return set(self.shell.settings.get("ovshell.pinned_apps", list) or [])

    def _set_pinned(self, pinned: Set[str], persist: bool = False):
        self.shell.settings.set(
            "ovshell.pinned_apps", sorted(pinned) or [], save=persist
        )


class OpenvarioShellImpl(OpenVarioShell):
    def __init__(
        self, screen: ScreenManager, config: str, rootfs: Optional[str]
    ) -> None:
        self.screen = screen
        if rootfs is None:
            self.os = ovos.OpenVarioOSImpl()
        else:
            print(f"Simulating Openvario on {rootfs}")
            self.os = ovos.OpenVarioOSSimulator(rootfs)
        self.settings = settings.StoredSettingsImpl.load(config)
        self.devices = device.DeviceManagerImpl()
        self.processes = process.ProcessManagerImpl()
        self.extensions = ExtensionManagerImpl()
        self.apps = AppManagerImpl(self)

    def boot(self) -> None:
        # Start extensions
        for ext in self.extensions.list_extensions():
            ext.start()

    def quit(self) -> None:
        raise urwid.ExitMainLoop()
