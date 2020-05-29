from typing import Callable, List, Optional
import asyncio
from dataclasses import dataclass

import urwid
import pytest

from ovshell import testing
from ovshell_core.upgradeapp import SystemUpgradeApp, SystemUpgradeActivity


def test_app_start(ovshell: testing.OpenVarioShellStub) -> None:
    # GIVEN
    app = SystemUpgradeApp(ovshell)

    # WHEN
    app.launch()

    # THEN
    act = ovshell.screen.stub_top_activity()
    assert isinstance(act, SystemUpgradeActivity)


def test_activity_initial_view(ovshell: testing.OpenVarioShellStub) -> None:
    # GIVEN
    act = SystemUpgradeActivity(ovshell)

    # WHEN
    wdg = act.create()
    view = _render(wdg)

    # THEN
    assert "System updates" in view


def _render(w: urwid.Widget) -> str:
    canvas = w.render((60, 40))
    contents = [t.decode("utf-8") for t in canvas.text]
    return "\n".join(contents)
