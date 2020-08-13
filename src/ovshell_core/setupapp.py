from typing import List

import urwid

from ovshell import api
from ovshell import widget


class SetupApp(api.App):
    name = "setup"
    title = "Setup"
    description = "System setup and calibration wizard"
    priority = 10

    def __init__(self, shell: api.OpenVarioShell):
        self.shell = shell

    def launch(self) -> None:
        act = SetupActivity(self.shell)
        self.shell.screen.push_activity(act)


class WizardStepWidget(urwid.WidgetWrap):
    signals = ["next"]
    title: str

    def next_step(self) -> None:
        self._emit("next")

    def make_next_button(self, title: str) -> urwid.Widget:
        btn = widget.PlainButton(title)
        urwid.connect_signal(btn, "click", self._on_next)
        return btn

    def _on_next(self, w: urwid.Widget) -> None:
        self.next_step()


class WelcomeWizardStep(WizardStepWidget):
    title = "Welcome to Openvario"

    def __init__(self, shell: api.OpenVarioShell) -> None:
        self.shell = shell

        welcome_msg = [
            "This wizard will guide you through setting up your ",
            ("highlight", "Openvario"),
            " device.",
        ]

        content = urwid.Pile(
            [
                ("pack", urwid.Text(welcome_msg)),
                ("pack", urwid.Divider()),
                (
                    "pack",
                    urwid.GridFlow([self.make_next_button("Start")], 12, 1, 1, "left"),
                ),
            ]
        )
        super().__init__(content)


class OrientationWizardStep(WizardStepWidget):
    title = "Pick device orientation"

    def __init__(self, shell: api.OpenVarioShell) -> None:
        self.shell = shell


class CalibrateTouchWizardStep(WizardStepWidget):
    title = "Calibrate touch screen"

    def __init__(self, shell: api.OpenVarioShell) -> None:
        self.shell = shell


class CalibrateSensorsWizardStep(WizardStepWidget):
    title = "Calibrate sensors"

    def __init__(self, shell: api.OpenVarioShell) -> None:
        self.shell = shell


class SetupActivity(api.Activity):
    def __init__(self, shell: api.OpenVarioShell) -> None:
        self.shell = shell

        self._setup_steps(
            [
                WelcomeWizardStep(shell),
                OrientationWizardStep(shell),
                CalibrateTouchWizardStep(shell),
                CalibrateSensorsWizardStep(shell),
            ]
        )

    def create(self) -> urwid.Widget:
        self.content = urwid.Filler(urwid.Padding(urwid.Text("Hello World")))

        self.title = urwid.Text("")
        self.step = urwid.WidgetPlaceholder(urwid.SolidFill(" "))

        self.frame = urwid.Frame(
            urwid.Pile([("pack", self.title), ("pack", urwid.Divider()), self.step,]),
            header=widget.ActivityHeader("Setup wizard"),
        )

        self._switch_step(0)
        return self.frame

    def _setup_steps(self, steps: List[WizardStepWidget]) -> None:
        assert len(steps) > 0
        self._steps = dict(enumerate(steps))

    def _switch_step(self, step_no: int) -> None:
        step_w = self._steps[step_no]
        total_steps = len(self._steps)
        self.title.set_text(
            [f"[{step_no + 1}/{total_steps}] ", ("highlight", f"{step_w.title}")]
        )
        self.step.original_widget = step_w
        self.frame._selectable = True
