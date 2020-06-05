from typing import Callable, List, Optional
import asyncio
from dataclasses import dataclass

import urwid
import pytest

from ovshell import testing
from ovshell_core.upgradeapp import OpkgTools
from ovshell_core.upgradeapp import SystemUpgradeApp, CheckForUpdatesActivity


class OpkgToolsStub(OpkgTools):
    opkg_binary = "echo"

    def __init__(self):
        pass

    def list_upgradables(self) -> List[str]:
        return []


def test_app_start(ovshell: testing.OpenVarioShellStub) -> None:
    # GIVEN
    app = SystemUpgradeApp(ovshell)

    # WHEN
    app.launch()

    # THEN
    act = ovshell.screen.stub_top_activity()
    assert isinstance(act, CheckForUpdatesActivity)


def test_activity_initial_view(ovshell: testing.OpenVarioShellStub) -> None:
    # GIVEN
    act = CheckForUpdatesActivity(ovshell, OpkgToolsStub())

    # WHEN
    wdg = act.create()
    view = _render(wdg)

    # THEN
    assert "System update" in view


@pytest.mark.asyncio
async def test_activity_no_updates(ovshell: testing.OpenVarioShellStub) -> None:
    act = CheckForUpdatesActivity(ovshell, OpkgToolsStub())
    wdg = act.create()

    # First render starts the command
    view = _render(wdg)
    assert "System update" in view
    assert "Checking for updates..." in view

    # Second render shows the output
    await asyncio.sleep(0.1)
    view = _render(wdg)
    assert "Checking for updates..." in view

    # Fourth render renders the finished command
    # await asyncio.sleep(0.1)
    view = _render(wdg)
    view = _render(wdg)
    assert "No updates found" in view


def _render(w: urwid.Widget) -> str:
    canvas = w.render((60, 30))
    contents = [t.decode("utf-8") for t in canvas.text]
    return "\n".join(contents)
