import asyncio
import os
from pathlib import Path

import pytest
from tests.conftest import ovshell
from typing import List, Tuple

import urwid

from ovshell import testing
from ovshell_core import setupapp


class TestSetupApp:
    def test_launch(self, ovshell: testing.OpenVarioShellStub) -> None:
        # GIVEN
        app = setupapp.SetupApp(ovshell, "test")

        # WHEN
        app.launch()

        # THEN
        act = ovshell.screen.stub_top_activity()
        assert isinstance(act, setupapp.SetupActivity)


class TestSetupActivity:
    def test_wizard_go_through(self, ovshell: testing.OpenVarioShellStub) -> None:
        # GIVEN
        act = setupapp.SetupActivity(ovshell, "test")
        ovshell.screen.push_activity(act)
        w = act.create()

        rendered = _render(w)
        assert "Setup wizard" in rendered
        assert "his wizard will guide you through" in rendered
        _keypress(w, ["enter"])

        rendered = _render(w)
        assert "Device orientation" in rendered
        _keypress(w, ["enter"])

        rendered = _render(w)
        assert "Touch screen calibration" in rendered
        _keypress(w, ["enter"])

        rendered = _render(w)
        assert "Sensor calibration" in rendered
        _keypress(w, ["enter"])

        rendered = _render(w)
        assert "Setup is complete" in rendered

        _keypress(w, ["enter"])
        assert ovshell.screen.stub_top_activity() is None


class TestOrientationWizardStep:
    def test_switch_orientation(self, ovshell: testing.OpenVarioShellStub) -> None:
        # GIVEN
        step = setupapp.OrientationWizardStep(ovshell)
        root = Path(ovshell.os.path("//"))
        root.joinpath("boot").mkdir()
        root.joinpath("sys", "class", "graphics", "fbcon").mkdir(parents=True)
        with open(root / "boot" / "config.uEnv", "w") as f:
            f.write("rotation=0")

        rendered = _render(step)
        assert "Skip" in rendered
        assert "Landscape" in rendered
        assert "Portrait" in rendered

        # WHEN
        _keypress(step, ["down", "down", "enter"])

        # THEN
        with open(ovshell.os.path("//sys/class/graphics/fbcon/rotate_all"), "r") as f:
            writtenrot = f.read()

        assert writtenrot == "3"

        setting = ovshell.settings.getstrict("core.screen_orientation", str)
        assert setting == "1"


class TestCalibrateTouchWizardStep:
    completed = False

    def setup_method(self):
        self.completed = False

    @pytest.mark.asyncio
    async def test_calibrate(self, ovshell: testing.OpenVarioShellStub) -> None:
        # GIVEN
        step = setupapp.CalibrateTouchWizardStep(ovshell)
        urwid.connect_signal(step, "next", self._completed)

        # WHEN
        _keypress(step, ["right", "enter"])
        topact = ovshell.screen.stub_top_activity()
        assert isinstance(topact, setupapp.CommandRunnerActivity)
        topact.create()
        topact.activate()

        await ovshell.screen.stub_wait_for_tasks(topact)

        assert self.completed == True

    def _completed(self, w: urwid.Widget) -> None:
        self.completed = True


class TestCalibrateSensorsWizardStep:
    completed = False

    def setup_method(self):
        self.completed = False

    @pytest.mark.asyncio
    async def test_calibrate(self, ovshell: testing.OpenVarioShellStub) -> None:
        # GIVEN
        step = setupapp.CalibrateSensorsWizardStep(ovshell)
        urwid.connect_signal(step, "next", self._completed)

        # WHEN
        _keypress(step, ["right", "enter"])
        topact = ovshell.screen.stub_top_activity()
        assert isinstance(topact, setupapp.CommandRunnerActivity)
        topact.create()
        topact.activate()

        await ovshell.screen.stub_wait_for_tasks(topact)

        assert self.completed == True

    def _completed(self, w: urwid.Widget) -> None:
        self.completed = True


class TestCommandRunnerActivity:
    completed = False

    def setup_method(self):
        self.completed = False

    @pytest.mark.asyncio
    async def test_success(self, ovshell: testing.OpenVarioShellStub) -> None:
        # GIVEN
        act = setupapp.CommandRunnerActivity(ovshell, "Test", "Running test", "cmd", [])
        ovshell.screen.push_activity(act)
        w = act.create()

        assert "Test" in _render(w)
        assert "Running test" in _render(w)

        # WHEN
        act.activate()
        await ovshell.screen.stub_wait_for_tasks(act)

        # THEN
        assert ovshell.screen.stub_top_activity() is None

    @pytest.mark.asyncio
    async def test_failure(self, ovshell: testing.OpenVarioShellStub) -> None:
        # GIVEN
        act = setupapp.CommandRunnerActivity(ovshell, "Test", "Running test", "cmd", [])
        act.on_failure(self._completed)
        ovshell.screen.push_activity(act)
        w = act.create()
        ovshell.os.stub_expect_run(2, stderr=b"Error happened")

        # WHEN
        act.activate()
        await ovshell.screen.stub_wait_for_tasks(act)

        # THEN
        dialog = ovshell.screen.stub_dialog()
        assert dialog is not None
        assert dialog.title == "Test"
        assert "Error happened" in _render(dialog.content)
        closed = dialog.stub_press_button("Close")
        assert closed
        assert self.completed

    def _completed(self) -> None:
        self.completed = True


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
