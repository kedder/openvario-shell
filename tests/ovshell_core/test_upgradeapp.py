from typing import Callable, List, Optional
import asyncio
from dataclasses import dataclass

import urwid
import pytest

from ovshell import testing
from ovshell_core.upgradeapp import OpkgTools
from ovshell_core.upgradeapp import SystemUpgradeApp, CheckForUpdatesActivity


class OpkgToolsStub(OpkgTools):
    opkg_binary = "true"

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


def _render(w: urwid.Widget) -> str:
    canvas = w.render((60, 40))
    contents = [t.decode("utf-8") for t in canvas.text]
    return "\n".join(contents)
