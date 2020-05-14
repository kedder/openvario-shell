from typing import List
import asyncio

import pytest
import urwid

from ovshell import protocol
from ovshell import testing
from ovshell.ui.mainmenu import MainMenuActivity


@pytest.fixture
def nosleep(monkeypatch) -> None:

    realsleep = asyncio.sleep

    async def nosleep(time: float) -> None:
        await realsleep(0)

    monkeypatch.setattr("asyncio.sleep", nosleep)


class MockExtension(protocol.Extension):
    id = "mock"
    title = "Mock Extension"


class MockApp(protocol.App):
    name = "mock"
    title = "Mock App"
    description = "Mock app for testing"
    priority = 0

    launched = False

    def launch(self) -> None:
        self.launched = True


def test_mainmenu_start_initial(ovshell: testing.OpenVarioShellStub) -> None:
    # GIVEN
    act = MainMenuActivity(ovshell)

    # WHEN
    w = act.create()

    # THEN
    rendered = _render(w)
    assert "Main Menu" in rendered
    assert "Applications" in rendered
    assert "Settings" in rendered


def test_mainmenu_exit(ovshell: testing.OpenVarioShellStub) -> None:
    # GIVEN
    act = MainMenuActivity(ovshell)
    w = act.create()

    # WHEN
    _keypress(w, ["esc"])

    # THEN
    quitact = ovshell.screen.stub_top_activity()
    assert quitact is not None
    qw = urwid.Filler(quitact.create())
    rendered = _render(qw)
    assert "Shut Down?" in rendered

    # Perform the shut down
    _keypress(qw, ["enter"])
    finalact = ovshell.screen.stub_top_activity()
    assert finalact is not None
    rendered = _render(finalact.create())
    assert "Openvario shutting down..." in rendered
    assert "OS: Shut down" in ovshell.get_stub_log()


@pytest.mark.asyncio
async def test_mainmenu_autostart_immediate(
    ovshell: testing.OpenVarioShellStub, nosleep: None
) -> None:
    # GIVEN
    app = MockApp()
    ovshell.apps.stub_add_app("mockapp", app, MockExtension())
    act = MainMenuActivity(ovshell, "mockapp")
    act.create()

    # WHEN
    act.activate()
    await asyncio.sleep(0)

    # THEN
    assert app.launched


@pytest.mark.asyncio
async def test_mainmenu_autostart_timeout(
    ovshell: testing.OpenVarioShellStub, nosleep: None
) -> None:
    # GIVEN
    app = MockApp()
    ovshell.apps.stub_add_app("mockapp", app, MockExtension())
    ovshell.settings.set("ovshell.autostart_app", "mockapp")
    ovshell.settings.set("ovshell.autostart_timeout", 3)
    act = MainMenuActivity(ovshell)
    w = act.create()

    # WHEN
    act.activate()
    await asyncio.sleep(0)
    await asyncio.sleep(0)

    # THEN
    rendered = _render(w)

    assert "Starting Mock App in" in rendered
    assert "Press any button to cancel" in rendered

    # Let the countdown finish
    assert act.autostart_countdown_task is not None
    await act.autostart_countdown_task
    rendered = _render(w)
    assert "Press any button to cancel" not in rendered
    assert app.launched


@pytest.mark.asyncio
async def test_mainmenu_autostart_cancel(
    ovshell: testing.OpenVarioShellStub, nosleep: None
) -> None:
    # GIVEN
    app = MockApp()
    ovshell.settings.set("ovshell.autostart_timeout", 3)
    ovshell.apps.stub_add_app("mockapp", app, MockExtension())
    act = MainMenuActivity(ovshell, "mockapp")
    w = act.create()
    act.activate()
    await asyncio.sleep(0)
    assert "Press any button to cancel" in _render(w)

    # WHEN
    _keypress(w, ["esc"])
    await asyncio.sleep(0)

    # THEN
    rendered = _render(w)
    assert "Press any button to cancel" not in rendered
    assert act.autostart_countdown_task is not None
    assert act.autostart_countdown_task.cancelled()


def _render(w: urwid.Widget) -> str:
    canvas = w.render((60, 40))
    contents = [t.decode("utf-8") for t in canvas.text]
    return "\n".join(contents)


def _keypress(w: urwid.Widget, keys: List[str]) -> None:
    for key in keys:
        nothandled = w.keypress((60, 40), key)
        assert nothandled is None
