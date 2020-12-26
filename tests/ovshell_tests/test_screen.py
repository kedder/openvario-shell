import asyncio
from typing import List

import mock
import pytest
import urwid

from ovshell import api
from ovshell.screen import ScreenManagerImpl
from tests.fixtures.urwid import UrwidMock


class ActivityStub(api.Activity):
    def __init__(self, text: str) -> None:
        self.text = text
        self.activated = 0
        self.destroyed = 0
        self.hidden = 0
        self.shown = 0

    def create(self) -> urwid.Widget:
        return urwid.Filler(urwid.Text(self.text, align="center"), "middle")

    def activate(self) -> None:
        self.activated += 1

    def destroy(self) -> None:
        self.destroyed += 1

    def hide(self) -> None:
        self.hidden += 1

    def show(self) -> None:
        self.shown += 1


def test_push_activity() -> None:
    urwid_mock = UrwidMock()
    mainloop = mock.Mock(name="MainLoop")
    screen = ScreenManagerImpl(mainloop)
    act = ActivityStub("Stub Activity")

    # WHEN
    screen.push_activity(act)

    # THEN
    act.activated == 1
    view = urwid_mock.render(mainloop.widget)
    assert "Stub Activity" in view


def test_pop_activity() -> None:
    # GIVEN
    # Create a basic palette and an urwid main loop - we are messing with the internal
    # implementation of palette handling.
    urwid_mock = UrwidMock()
    palette = [
        ("text", "white", "black", ""),
    ]
    asyncioloop = asyncio.get_event_loop()
    evl = urwid.AsyncioEventLoop(loop=asyncioloop)
    mainloop = urwid.MainLoop(None, palette=palette, event_loop=evl)

    screen = ScreenManagerImpl(mainloop)
    act1 = ActivityStub("Activity One")
    act2 = ActivityStub("Activity Two")
    screen.push_activity(act1)
    screen.push_activity(act2)

    assert "Activity Two" in urwid_mock.render(mainloop.widget)

    # WHEN
    screen.pop_activity()

    # THEN
    assert "Activity One" in urwid_mock.render(mainloop.widget)
    assert act2.activated == 1
    assert act2.destroyed == 1
    assert act2.shown == 1
    assert act2.hidden == 1

    assert act1.activated == 1
    assert act1.shown == 2
    assert act1.hidden == 1


def test_push_modal() -> None:
    urwid_mock = UrwidMock()
    mainloop = mock.Mock(name="MainLoop")
    mainloop.screen._palette = {}
    screen = ScreenManagerImpl(mainloop)
    act1 = ActivityStub("Activity One")
    screen.push_activity(act1)

    # WHEN
    screen.push_modal(
        ActivityStub("Modal Activity"),
        api.ModalOptions(align="center", width=20, valign="top", height=3),
    )

    # THEN
    # Modal activity does not obscure the main view
    view = urwid_mock.render(mainloop.widget)
    assert "Modal Activity" in view
    assert "Activity One" in view


def test_push_dialog() -> None:
    # GIVEN
    urwid_mock = UrwidMock()
    mainloop = mock.Mock(name="MainLoop")
    mainloop.screen._palette = {}
    screen = ScreenManagerImpl(mainloop)
    act1 = ActivityStub("Main Activity")
    screen.push_activity(act1)

    # WHEN
    dialog = screen.push_dialog("Dialog Title", urwid.Text("Dialog content"))
    dialog.add_button("Nevermind", lambda: False)
    dialog.add_button("Close", lambda: True)

    # THEN
    view = urwid_mock.render(mainloop.widget)
    assert "Dialog Title" in view
    assert "Dialog content" in view
    assert "Close" in view
    assert "Nevermind" in view

    # WHEN
    # Click the default button (Nevermind)
    urwid_mock.keypress(mainloop.widget, ["enter"])

    # THEN
    # Dialog did not close
    assert "Dialog Title" in urwid_mock.render(mainloop.widget)

    # WHEN
    # Click the "close" button
    urwid_mock.keypress(mainloop.widget, ["right", "enter"])

    # THEN
    # Dialog closed
    assert "Dialog Title" not in urwid_mock.render(mainloop.widget)


@pytest.mark.asyncio
async def test_spawn_task() -> None:
    # GIVEN
    mainloop = mock.Mock(name="MainLoop")
    mainloop.screen._palette = {}
    screen = ScreenManagerImpl(mainloop)
    act1 = ActivityStub("Main Activity")
    screen.push_activity(act1)

    log: List[str] = []

    async def infinite_loop() -> None:
        log.append("started")
        while True:
            try:
                await asyncio.sleep(0.1)
            except asyncio.CancelledError:
                log.append("cancelled")
                raise

    # WHEN
    screen.spawn_task(act1, infinite_loop())
    await asyncio.sleep(0)

    # THEN
    assert log == ["started"]

    # WHEN
    screen.pop_activity()
    await asyncio.sleep(0)

    # THEN
    assert log == ["started", "cancelled"]


def test_set_indicator_simple() -> None:
    urwid_mock = UrwidMock()
    mainloop = mock.Mock(urwid.MainLoop)
    screen = ScreenManagerImpl(mainloop)

    screen.set_indicator("test", "Hello World", api.IndicatorLocation.LEFT, 0)

    view = urwid_mock.render(mainloop.widget)
    assert "Hello World" in view

    screen.remove_indicator("test")
    view = urwid_mock.render(mainloop.widget)
    assert "Hello World" not in view


def test_set_indicator_ordering() -> None:
    # GIVEN
    urwid_mock = UrwidMock()
    mainloop = mock.Mock(urwid.MainLoop)
    screen = ScreenManagerImpl(mainloop)
    screen.set_indicator("3", "Three", api.IndicatorLocation.RIGHT, 3)
    screen.set_indicator("1", "One", api.IndicatorLocation.RIGHT, 1)
    screen.set_indicator("2", ["T", "w", "o"], api.IndicatorLocation.RIGHT, 2)

    # WHEN
    view = urwid_mock.render(mainloop.widget)

    # THEN
    assert "One Two Three" in view
