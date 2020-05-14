from typing import Callable, List, Optional
import asyncio

import urwid

import ovshell
from ovshell import protocol
from ovshell import widget
from ovshell.ui.settings import SettingsActivity
from ovshell.ui.apps import AppsActivity


class DialogActivity(protocol.Activity):
    button_widgets: List[urwid.Widget]

    def __init__(self, screen: protocol.ScreenManager, title: str, message: str):
        self.screen = screen
        self.title = title
        self.message = message
        self.modal_opts = protocol.ModalOptions(
            align="center",
            width=("relative", 60),
            valign="middle",
            height="pack",
            min_width=54,
        )

        self.button_widgets = []

    def create(self) -> urwid.Widget:
        msg = urwid.Text(self.message)

        buttons = urwid.GridFlow(
            self.button_widgets, cell_width=11, h_sep=2, v_sep=1, align="center",
        )

        view = urwid.LineBox(urwid.Pile([msg, urwid.Divider(), buttons]), self.title)

        return view

    def add_button(self, label: str, handler: Callable[[], bool]) -> None:
        button = widget.PlainButton(label)
        urwid.connect_signal(
            button, "click", self._on_button_clicked, user_args=[handler]
        )
        self.button_widgets.append(button)

    def _on_button_clicked(
        self, handler: Callable[[], bool], btn: urwid.Widget
    ) -> None:
        close_activity = handler()
        if close_activity:
            self.screen.pop_activity()


class FinalScreenActivity(protocol.Activity):
    def __init__(self, message: str) -> None:
        self.message = message

    def create(self) -> urwid.Widget:
        msg = urwid.Text(self.message)
        haligned = urwid.Padding(msg, width=len(self.message), align="center")
        valigned = urwid.Filler(haligned, "middle")
        # Wrap in KeySignals to intercept all escape keypresses
        return widget.KeySignals(valigned)


class MainMenuActivity(protocol.Activity):
    autostart_app_id: Optional[str]
    autostart_progess: urwid.ProgressBar
    autostart_countdown_task: Optional[asyncio.Task] = None
    autostart_canceller: "AutostartCanceller"

    def __init__(
        self, shell: protocol.OpenVarioShell, autostart_app_id: str = None
    ) -> None:
        self.shell = shell
        self.autostart_app_id = autostart_app_id

    def create(self) -> urwid.Widget:
        btxt = urwid.BigText("Openvario", urwid.font.Thin6x6Font())
        logo = urwid.Padding(btxt, "center", "clip")

        m_pinned_apps = self._get_pinned_apps()
        if m_pinned_apps:
            m_pinned_apps.append(urwid.Divider())

        m_apps = widget.SelectableListItem("Applications")
        urwid.connect_signal(m_apps, "click", self._on_apps)
        m_settings = widget.SelectableListItem("Settings")
        urwid.connect_signal(m_settings, "click", self._on_settings)
        m_shutdown = widget.SelectableListItem("Shut down")
        urwid.connect_signal(m_shutdown, "click", self._on_quit)
        menu = urwid.Pile(
            m_pinned_apps + [m_apps, m_settings, urwid.Divider(), m_shutdown]
        )

        # Reserve space for counter
        self.autostart_counter = urwid.WidgetPlaceholder(
            urwid.BoxAdapter(urwid.SolidFill(" "), 2)
        )

        view = urwid.Filler(
            urwid.Pile(
                [
                    logo,
                    urwid.Text(self._get_version(), align=urwid.CENTER),
                    urwid.Divider(),
                    urwid.Padding(
                        urwid.LineBox(menu, "Main Menu", title_align="left"),
                        width=("relative", 40),
                        align=urwid.CENTER,
                    ),
                    urwid.Divider(),
                    urwid.Divider(),
                    self.autostart_counter,
                ]
            ),
            "middle",
        )
        self.autostart_canceller = AutostartCanceller(view)
        urwid.connect_signal(
            self.autostart_canceller, "anykey", self._on_cancel_autostart
        )
        view = widget.KeySignals(self.autostart_canceller)
        urwid.connect_signal(view, "cancel", self._on_quit)
        return view

    def activate(self) -> None:
        autostart = self._get_autostart_app()
        timeout = self.shell.settings.get("ovshell.autostart_timeout", int) or 0
        if autostart is not None:
            self.autostart_countdown_task = self.shell.screen.spawn_task(
                self, self.autostart_countdown(timeout, autostart)
            )

    def _get_pinned_apps(self) -> urwid.Widget:
        m_items = []
        for appinfo in self.shell.apps.list():
            if not appinfo.pinned:
                continue

            button = widget.SelectableListItem(appinfo.app.title)
            urwid.connect_signal(
                button, "click", self._on_pinned_app, user_args=[appinfo]
            )
            m_items.append(button)

        return m_items

    def _on_settings(self, w: urwid.Widget) -> None:
        settings_act = SettingsActivity(self.shell)
        self.shell.screen.push_activity(settings_act)

    def _on_apps(self, w: urwid.Widget) -> None:
        apps_act = AppsActivity(self.shell)
        self.shell.screen.push_activity(apps_act)

    def _on_pinned_app(self, appinfo: protocol.AppInfo, w: urwid.Widget) -> None:
        appinfo.app.launch()

    def _on_quit(self, w: urwid.Widget) -> None:
        confirm = DialogActivity(
            self.shell.screen,
            "Shut Down?",
            "Do you really want to shut down Openvario?",
        )
        confirm.add_button("Shut Down", self._on_shutdown)
        confirm.add_button("Restart", self._on_restart)
        confirm.add_button("Shell", self._on_exit)
        confirm.add_button("Cancel", lambda: True)
        self.shell.screen.push_modal(confirm, confirm.modal_opts)

    def _on_shutdown(self) -> bool:
        self.shell.screen.push_activity(
            FinalScreenActivity("Openvario shutting down...")
        )
        self.shell.os.shut_down()
        return False

    def _on_exit(self) -> bool:
        self.shell.quit()
        return True

    def _on_restart(self) -> bool:
        self.shell.screen.push_activity(FinalScreenActivity("Openvario restarting..."))
        self.shell.os.restart()
        return False

    def destroy(self) -> None:
        pass

    def _get_version(self) -> str:
        return f"Version {ovshell.__version__}"

    def _get_autostart_app(self) -> Optional[protocol.AppInfo]:
        app_id = self.autostart_app_id
        app_id = app_id or self.shell.settings.get("ovshell.autostart_app", str)
        if app_id is None:
            return None

        appinfo = self.shell.apps.get(app_id)
        if appinfo is not None:
            return appinfo

        availapps = ", ".join([a.id for a in self.shell.apps.list()])
        print(
            f"Error: app '{self.autostart_app_id}' does not exist. "
            f"Available apps: {availapps}"
        )
        return None

    def _make_countdown_widget(self) -> urwid.Widget:
        self.autostart_progress = AutostartProgressBar(
            "pg inverted", "pg complete", current=40
        )
        self.autostart_progress.static_text = ""

        counter_pile = urwid.Pile(
            [
                self.autostart_progress,
                urwid.Text(("remark", "Press any button to cancel")),
            ]
        )

        # Align with main menu
        return urwid.Padding(counter_pile, width=("relative", 80), align="center",)

    async def autostart_countdown(self, countdown: int, appinfo: protocol.AppInfo):
        empty_widget = self.autostart_counter.original_widget
        self.autostart_counter.original_widget = self._make_countdown_widget()
        self.autostart_canceller.active = True
        try:
            if countdown > 0:
                await self._run_countdown(countdown, appinfo.app.title)
            appinfo.app.launch()
        finally:
            # Clean up the progress indicator when done or cancelled
            self.autostart_counter.original_widget = empty_widget
            self.autostart_canceller.active = False

    async def _run_countdown(self, countdown: int, appname: str):
        current = float(countdown)
        delta = 0.1
        self.autostart_progress.set_completion(100)
        while current >= 0:
            await asyncio.sleep(delta)
            current -= delta
            progress = int(current / countdown * 100)
            self.autostart_progress.set_completion(progress)
            status = f"Starting {appname} in {int(current + 1)}s"
            self.autostart_progress.static_text = status

    def _on_cancel_autostart(self, w: urwid.Widget) -> None:
        if self.autostart_countdown_task is None:
            return
        self.autostart_countdown_task.cancel()


class AutostartProgressBar(urwid.ProgressBar):
    static_text: Optional[str] = None

    def get_text(self) -> str:
        if self.static_text is not None:
            return self.static_text
        return super().get_text()


class AutostartCanceller(urwid.WidgetWrap):
    """Emmit "anykey" signal to cancel autostart counter"""

    signals = ["anykey"]
    active = False

    def keypress(self, size, key: str) -> Optional[str]:
        if self.active:
            self._emit("anykey")
            # When active, use escape to simply cancel the autostart. Do not
            # propagate it further, because that would bring "shut down"
            # dialog.
            if key == "esc":
                return None
        return super().keypress(size, key)
