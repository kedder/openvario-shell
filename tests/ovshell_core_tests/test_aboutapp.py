from typing import Dict, List, Optional, Tuple
import asyncio
import pytest

import urwid

from ovshell import testing
from ovshell_core import aboutapp
from ovshell_core.sysinfo import SystemInfo


class SystemInfoStub(SystemInfo):
    pkg_versions: Dict[str, str]

    def __init__(self) -> None:
        self.pkg_versions = {}

    async def get_openvario_version(self) -> Optional[str]:
        return "00000 (stub)"

    async def get_installed_package_version(self, package_name: str) -> Optional[str]:
        return self.pkg_versions.get(package_name)

    async def get_kernel_version(self) -> Optional[str]:
        return "5.7.0-stub"

    async def get_hostname(self) -> Optional[str]:
        return "openvario-stub"


class TestAboutApp:
    def test_launch(self, ovshell: testing.OpenVarioShellStub) -> None:
        # GIVEN
        app = aboutapp.AboutApp(ovshell)

        # WHEN
        app.launch()

        # THEN
        act = ovshell.screen.stub_top_activity()
        assert isinstance(act, aboutapp.AboutActivity)


class TestAboutActivity:
    @pytest.mark.asyncio
    async def test_wizard_diplay(self, ovshell: testing.OpenVarioShellStub) -> None:
        # GIVEN
        sys_info_stub = SystemInfoStub()
        sys_info_stub.pkg_versions = {"xcsoar-testing": "7.0.0-preview15"}
        act = aboutapp.AboutActivity(ovshell)
        act.sys_info = sys_info_stub
        w = act.create()
        act.activate()

        rendered = _render(w)
        assert "About Openvario" in rendered
        assert "..." in rendered  # versions are not populated initially

        # WHEN
        # wait for all versions to be fetched
        await ovshell.screen.stub_wait_for_tasks(act)

        rendered = _render(w)
        assert "..." not in rendered
        assert "N/A" in rendered
        assert "7.0.0-preview15" in rendered
        assert "00000 (stub)" in rendered


def _render(w: urwid.Widget) -> str:
    canvas = w.render(_get_size(w))
    contents = [t.decode("utf-8") for t in canvas.text]
    return "\n".join(contents)


def _keypress(w: urwid.Widget, keys: List[str]) -> None:
    for key in keys:
        nothandled = w.keypress(_get_size(w), key)
        assert nothandled is None


def _get_size(w: urwid.Widget) -> Tuple[int, ...]:
    size: Tuple[int, ...] = (60, 40)
    if "flow" in w.sizing():
        size = (60,)
    return size
