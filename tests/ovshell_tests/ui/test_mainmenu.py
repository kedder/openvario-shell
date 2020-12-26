import asyncio

import pytest

from ovshell import api, testing
from ovshell.ui.mainmenu import MainMenuActivity
from tests.fixtures.urwid import UrwidMock


@pytest.fixture
def nosleep(monkeypatch) -> None:

    realsleep = asyncio.sleep

    async def nosleep(time: float) -> None:
        await realsleep(0)

    monkeypatch.setattr("asyncio.sleep", nosleep)


class MockExtension(api.Extension):
    id = "mock"
    title = "Mock Extension"


class MockApp(api.App):
    name = "mock"
    title = "Mock App"
    description = "Mock app for testing"
    priority = 0

    launched = False

    def launch(self) -> None:
        self.launched = True


def test_mainmenu_start_initial(ovshell: testing.OpenVarioShellStub) -> None:
    # GIVEN
    urwid_mock = UrwidMock()
    act = MainMenuActivity(ovshell)

    # WHEN
    w = act.create()

    # THEN
    rendered = urwid_mock.render(w)
    assert "Main Menu" in rendered
    assert "Applications" in rendered
    assert "Settings" in rendered


def test_mainmenu_exit(ovshell: testing.OpenVarioShellStub) -> None:
    # GIVEN
    urwid_mock = UrwidMock()
    act = MainMenuActivity(ovshell)
    w = act.create()

    # WHEN
    urwid_mock.keypress(w, ["esc"])

    # THEN
    quitdialog = ovshell.screen.stub_dialog()
    assert quitdialog is not None
    assert quitdialog.title == "Shut Down?"

    # Perform the shut down
    closed = quitdialog.stub_press_button("Shut Down")
    assert not closed
    finalact = ovshell.screen.stub_top_activity()
    assert finalact is not None
    rendered = urwid_mock.render(finalact.create())
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
    urwid_mock = UrwidMock()
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
    rendered = urwid_mock.render(w)

    assert "Starting Mock App in" in rendered
    assert "Press any button to cancel" in rendered

    # Let the countdown finish
    assert act.autostart_countdown_task is not None
    await act.autostart_countdown_task
    rendered = urwid_mock.render(w)
    assert "Press any button to cancel" not in rendered
    assert app.launched


@pytest.mark.asyncio
async def test_mainmenu_autostart_cancel(
    ovshell: testing.OpenVarioShellStub, nosleep: None
) -> None:
    # GIVEN
    urwid_mock = UrwidMock()
    app = MockApp()
    ovshell.settings.set("ovshell.autostart_timeout", 3)
    ovshell.apps.stub_add_app("mockapp", app, MockExtension())
    act = MainMenuActivity(ovshell, "mockapp")
    w = act.create()
    act.activate()
    await asyncio.sleep(0)
    assert "Press any button to cancel" in urwid_mock.render(w)

    # WHEN
    urwid_mock.keypress(w, ["esc"])
    await asyncio.sleep(0)

    # THEN
    rendered = urwid_mock.render(w)
    assert "Press any button to cancel" not in rendered
    assert act.autostart_countdown_task is not None
    assert act.autostart_countdown_task.cancelled()
