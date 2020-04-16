from typing import Callable, List

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
    def __init__(self, shell: protocol.OpenVarioShell) -> None:
        self.shell = shell

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
                ]
            ),
            "middle",
        )
        view = widget.KeySignals(view)
        urwid.connect_signal(view, "cancel", self._on_quit)
        return view

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

    def activate(self) -> None:
        pass

    def destroy(self) -> None:
        pass

    def _get_version(self) -> str:
        return f"Version {ovshell.__version__}"
