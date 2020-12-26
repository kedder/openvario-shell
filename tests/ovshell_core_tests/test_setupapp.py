from pathlib import Path

import pytest
import urwid

from ovshell import testing
from ovshell_core import setupapp
from tests.fixtures.urwid import UrwidMock


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
        urwid_mock = UrwidMock()
        act = setupapp.SetupActivity(ovshell, "test")
        ovshell.screen.push_activity(act)
        w = act.create()

        rendered = urwid_mock.render(w)
        assert "Setup wizard" in rendered
        assert "his wizard will guide you through" in rendered
        urwid_mock.keypress(w, ["enter"])

        rendered = urwid_mock.render(w)
        assert "Device orientation" in rendered
        urwid_mock.keypress(w, ["enter"])

        rendered = urwid_mock.render(w)
        assert "Touch screen calibration" in rendered
        urwid_mock.keypress(w, ["enter"])

        rendered = urwid_mock.render(w)
        assert "Sensor calibration" in rendered
        urwid_mock.keypress(w, ["enter"])

        rendered = urwid_mock.render(w)
        assert "Setup is complete" in rendered

        urwid_mock.keypress(w, ["enter"])
        assert ovshell.screen.stub_top_activity() is None


class TestOrientationWizardStep:
    def test_switch_orientation(self, ovshell: testing.OpenVarioShellStub) -> None:
        # GIVEN
        urwid_mock = UrwidMock()
        step = setupapp.OrientationWizardStep(ovshell)
        root = Path(ovshell.os.path("//"))
        root.joinpath("boot").mkdir()
        root.joinpath("sys", "class", "graphics", "fbcon").mkdir(parents=True)
        with open(root / "boot" / "config.uEnv", "w") as f:
            f.write("rotation=0")

        rendered = urwid_mock.render(step)
        assert "Skip" in rendered
        assert "Landscape" in rendered
        assert "Portrait" in rendered

        # WHEN
        urwid_mock.keypress(step, ["down", "down", "enter"])

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
        urwid_mock = UrwidMock()
        step = setupapp.CalibrateTouchWizardStep(ovshell)
        urwid.connect_signal(step, "next", self._completed)

        # WHEN
        urwid_mock.keypress(step, ["right", "enter"])
        topact = ovshell.screen.stub_top_activity()
        assert isinstance(topact, setupapp.CommandRunnerActivity)
        topact.create()
        topact.activate()

        await ovshell.screen.stub_wait_for_tasks(topact)

        assert self.completed is True

    def _completed(self, w: urwid.Widget) -> None:
        self.completed = True


class TestCalibrateSensorsWizardStep:
    completed = False

    def setup_method(self):
        self.completed = False

    @pytest.mark.asyncio
    async def test_calibrate(self, ovshell: testing.OpenVarioShellStub) -> None:
        # GIVEN
        urwid_mock = UrwidMock()
        step = setupapp.CalibrateSensorsWizardStep(ovshell)
        urwid.connect_signal(step, "next", self._completed)

        # WHEN
        urwid_mock.keypress(step, ["right", "enter"])
        topact = ovshell.screen.stub_top_activity()
        assert isinstance(topact, setupapp.CommandRunnerActivity)
        topact.create()
        topact.activate()

        await ovshell.screen.stub_wait_for_tasks(topact)

        assert self.completed is True

    def _completed(self, w: urwid.Widget) -> None:
        self.completed = True


class TestCommandRunnerActivity:
    completed = False

    def setup_method(self):
        self.completed = False

    @pytest.mark.asyncio
    async def test_success(self, ovshell: testing.OpenVarioShellStub) -> None:
        # GIVEN
        urwid_mock = UrwidMock()
        act = setupapp.CommandRunnerActivity(ovshell, "Test", "Running test", "cmd", [])
        ovshell.screen.push_activity(act)
        w = act.create()

        assert "Test" in urwid_mock.render(w)
        assert "Running test" in urwid_mock.render(w)

        # WHEN
        act.activate()
        await ovshell.screen.stub_wait_for_tasks(act)

        # THEN
        assert ovshell.screen.stub_top_activity() is None

    @pytest.mark.asyncio
    async def test_failure(self, ovshell: testing.OpenVarioShellStub) -> None:
        # GIVEN
        urwid_mock = UrwidMock()
        act = setupapp.CommandRunnerActivity(ovshell, "Test", "Running test", "cmd", [])
        act.on_failure(self._completed)
        ovshell.screen.push_activity(act)
        act.create()
        ovshell.os.stub_expect_run(2, stderr=b"Error happened")

        # WHEN
        act.activate()
        await ovshell.screen.stub_wait_for_tasks(act)

        # THEN
        dialog = ovshell.screen.stub_dialog()
        assert dialog is not None
        assert dialog.title == "Test"
        assert "Error happened" in urwid_mock.render(dialog.content)
        closed = dialog.stub_press_button("Close")
        assert closed
        assert self.completed

    def _completed(self) -> None:
        self.completed = True
