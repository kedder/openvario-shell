import asyncio
from typing import Callable, List

import urwid

from ovshell import api, widget
from ovshell_core import rotation


class SetupApp(api.App):
    name = "setup"
    title = "Initial Setup"
    description = "System setup and calibration wizard"
    priority = 10

    def __init__(self, shell: api.OpenVarioShell, ext_id: str) -> None:
        self.shell = shell
        self.ext_id = ext_id

    def install(self, appinfo: api.AppInfo) -> None:
        self.shell.apps.pin(appinfo)

    def launch(self) -> None:
        app_id = f"{self.ext_id}.{self.name}"
        act = SetupActivity(self.shell, app_id)
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
                ("pack", _button_row([self.make_next_button("Start")]),),
            ]
        )
        super().__init__(content)


class OrientationWizardStep(WizardStepWidget):
    title = "Device orientation"

    def __init__(self, shell: api.OpenVarioShell) -> None:
        self.shell = shell

        msg = [
            "Orient your Openvario device the way it will be mounted on ",
            "your instrument panel. Press ",
            ("highlight", "↓"),
            " and ",
            ("highlight", "↑"),
            " until orientation looks right. Press ",
            ("highlight", "Enter"),
            " to confirm.",
        ]

        orient_walker = urwid.SimpleFocusListWalker([])
        for oval, otxt in rotation.get_rotations():
            mitem = widget.SelectableListItem(otxt)
            urwid.connect_signal(
                mitem, "click", self._save_orientation, user_args=[oval]
            )
            orient_walker.append(mitem)

        self.orient_lb = urwid.ListBox(orient_walker)
        self._set_current_rotation(self.orient_lb)
        urwid.connect_signal(orient_walker, "modified", self._on_focus_changed)

        content = urwid.Pile(
            [
                ("pack", urwid.Text(msg)),
                ("pack", urwid.Divider()),
                ("pack", _button_row([self.make_next_button("Skip")]),),
                ("pack", urwid.Divider()),
                (len(orient_walker), self.orient_lb),
            ]
        )
        super().__init__(content)

    def _set_current_rotation(self, lb: urwid.ListBox) -> None:
        rots = [n for n, title in rotation.get_rotations()]
        cur_rot = self.shell.settings.get("core.screen_orientation", str) or "0"
        focus_pos = rots.index(cur_rot)
        lb.set_focus(focus_pos, "above")

    def _on_focus_changed(self) -> None:
        focus = self._w.get_focus_widgets()
        if self.orient_lb not in focus:
            # Do not change orientation until listbox is in focus
            return

        _, idx = self.orient_lb.get_focus()
        rots = rotation.get_rotations()
        rot, _ = rots[idx]
        rotation.apply_rotation(self.shell.os, rot)

    def _save_orientation(self, orient: str, w: urwid.Widget) -> None:
        self.shell.settings.set("core.screen_orientation", orient, save=True)
        self.next_step()


class CalibrateTouchWizardStep(WizardStepWidget):
    title = "Touch screen calibration"

    cal_scipt = "//usr/bin/ov-calibrate-ts.sh"

    def __init__(self, shell: api.OpenVarioShell) -> None:
        self.shell = shell

        msg = [
            "If your Openvario is equipped with a touch-screen, ",
            "it needs to be calibrated. You will need to press the indicated ",
            "areas of the screen. It is recommended to press resistive ",
            "touch-screen with your fingernail.",
            "\n\n",
            "If touch-screen is not installed, skip this step.",
        ]

        cal_btn = widget.PlainButton("Calibrate")
        urwid.connect_signal(cal_btn, "click", self._on_calibrate)

        content = urwid.Pile(
            [
                ("pack", urwid.Text(msg)),
                ("pack", urwid.Divider()),
                ("pack", _button_row([self.make_next_button("Skip"), cal_btn]),),
            ]
        )
        super().__init__(content)

    def _on_calibrate(self, w: urwid.Widget) -> None:
        cmd = self.shell.os.path(self.cal_scipt)
        runact = CommandRunnerActivity(
            self.shell,
            "Touch screen calibration",
            "Calibrating touch screen. Please wait...",
            cmd,
            [],
        )
        runact.on_success(self._on_calibrate_complete)
        self.shell.screen.push_modal(runact, runact.get_modal_opts())

    def _on_calibrate_complete(self) -> None:
        self.next_step()


class CalibrateSensorsWizardStep(WizardStepWidget):
    title = "Sensor calibration"

    cal_script = "//opt/bin/sensorcal"
    cal_args = ["-i", "-c"]

    def __init__(self, shell: api.OpenVarioShell) -> None:
        self.shell = shell

        msg = [
            "If your Openvario has sensorboard connected, calibrate sensors here. ",
            "\n\n",
            "If sensors are not installed, skip this step.",
        ]

        cal_btn = widget.PlainButton("Calibrate")
        urwid.connect_signal(cal_btn, "click", self._on_calibrate)

        content = urwid.Pile(
            [
                ("pack", urwid.Text(msg)),
                ("pack", urwid.Divider()),
                ("pack", _button_row([self.make_next_button("Skip"), cal_btn]),),
            ]
        )
        super().__init__(content)

    def _on_calibrate(self, w: urwid.Widget) -> None:
        cmd = self.shell.os.path(self.cal_script)
        runact = CommandRunnerActivity(
            self.shell,
            "Sensor screen calibration",
            "Calibrating sensors. Please wait...",
            cmd,
            self.cal_args,
        )
        runact.on_success(self._on_calibrate_complete)
        self.shell.screen.push_modal(runact, runact.get_modal_opts())

    def _on_calibrate_complete(self) -> None:
        self.next_step()


class SetupActivity(api.Activity):
    def __init__(self, shell: api.OpenVarioShell, app_id: str) -> None:
        self.shell = shell
        self.app_id = app_id

        self._setup_steps(
            [
                WelcomeWizardStep(shell),
                OrientationWizardStep(shell),
                CalibrateTouchWizardStep(shell),
                CalibrateSensorsWizardStep(shell),
            ]
        )

    def create(self) -> urwid.Widget:
        self.content = urwid.Filler(urwid.Padding(urwid.Text("")))

        self.title = urwid.Text("")
        self.step = urwid.WidgetPlaceholder(urwid.SolidFill(" "))

        self.content_pile = urwid.Pile(
            [("pack", self.title), ("pack", urwid.Divider()), self.step]
        )

        self.frame = urwid.Frame(
            self.content_pile, header=widget.ActivityHeader("Setup wizard"),
        )

        self._switch_step(0)
        return self.frame

    def _setup_steps(self, steps: List[WizardStepWidget]) -> None:
        assert len(steps) > 0
        self._steps = {}
        for n, step_w in enumerate(steps):
            if n + 1 == len(steps):
                next_handler = self._on_wizard_completed
            else:

                def next_handler(w: urwid.Widget, sn=n + 1) -> None:
                    self._switch_step(sn)

            urwid.connect_signal(step_w, "next", next_handler)
            self._steps[n] = step_w
        self._steps = dict(enumerate(steps))

    def _switch_step(self, step_no: int) -> None:
        step_w = self._steps[step_no]
        total_steps = len(self._steps)
        self.title.set_text(
            [f"[{step_no + 1}/{total_steps}] ", ("highlight", f"{step_w.title}")]
        )
        self.step.original_widget = urwid.Filler(step_w, valign="top")
        self.content_pile.set_focus(self.step)
        self.content_pile._selectable = True

    def _on_wizard_completed(self, w: urwid.Widget) -> None:
        done_msg = [
            ("highlight", "Setup is complete"),
            "\n\n",
            "Openvario is ready to use. Happy flying!",
        ]

        exit_btn = widget.PlainButton("Exit")
        urwid.connect_signal(exit_btn, "click", self._on_exit)

        done_contents = [
            (urwid.Text(done_msg), ("pack", None)),
            (urwid.Divider(), ("pack", None)),
            (_button_row([exit_btn]), ("pack", None)),
            (urwid.SolidFill(" "), ("weight", 1)),
        ]
        self.content_pile.contents = done_contents

    def _on_exit(self, w: urwid.Widget) -> None:
        # Unpin setup app after the first use
        appinfo = self.shell.apps.get(self.app_id)
        if appinfo is not None and appinfo.pinned:
            self.shell.apps.unpin(appinfo, persist=True)
        self.shell.screen.pop_activity()


def _button_row(buttons: List[urwid.Widget]) -> urwid.GridFlow:
    return urwid.GridFlow(buttons, 14, 1, 1, "left")


class CommandRunnerActivity(api.Activity):
    _success_handlers: List[Callable[[], None]]
    _failure_handlers: List[Callable[[], None]]

    def __init__(
        self,
        shell: api.OpenVarioShell,
        title: str,
        description: str,
        command: str,
        args: List[str],
    ) -> None:
        self.shell = shell
        self.title = title
        self.description = description
        self.command = command
        self.args = args

        self._success_handlers = []
        self._failure_handlers = []

    def create(self) -> urwid.Widget:
        message = urwid.Text(self.description)
        self.contents = urwid.Pile([message])
        return urwid.LineBox(self.contents, title=self.title)

    def get_modal_opts(self) -> api.ModalOptions:
        return api.ModalOptions(
            align="center", width=("relative", 90), valign="middle", height="pack",
        )

    def activate(self) -> None:
        self.shell.screen.spawn_task(self, self.run(self.command, self.args))

    def on_success(self, handler: Callable[[], None]) -> None:
        self._success_handlers.append(handler)

    def on_failure(self, handler: Callable[[], None]) -> None:
        self._failure_handlers.append(handler)

    async def run(self, command: str, args: List[str]) -> None:
        proc = await self.shell.os.run(command, args)
        result = await proc.wait()
        loop = asyncio.get_event_loop()
        if result != 0:
            errors = await proc.stderr.read()
            loop.call_soon(self._handle_error, result, errors.decode())
        else:
            loop.call_soon(self._handle_success)

    def _handle_error(self, result: int, errors: str) -> None:
        self.shell.screen.pop_activity()
        error_msg = urwid.Text([("error message", "Command failed"), "\n\n", errors])
        dialog = self.shell.screen.push_dialog(self.title, error_msg)
        dialog.add_button("Close", self._run_error_handlers)

    def _handle_success(self) -> None:
        self.shell.screen.pop_activity()
        for h in self._success_handlers:
            h()

    def _run_error_handlers(self) -> bool:
        for h in self._failure_handlers:
            h()
        return True
