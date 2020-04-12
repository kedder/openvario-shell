import urwid

from ovshell.protocol import OpenVarioShell
from ovshell import widget
from ovshell.ui.settings import SettingsActivity
from ovshell.ui.apps import AppsActivity


class MainMenuActivity:
    def __init__(self, shell: OpenVarioShell) -> None:
        self.shell = shell

    def create(self) -> urwid.Widget:
        btxt = urwid.BigText("Openvario", urwid.font.Thin6x6Font())
        logo = urwid.Padding(btxt, "center", "clip")

        m_apps = widget.SelectableListItem("Apps")
        urwid.connect_signal(m_apps, "click", self._on_apps)
        m_settings = widget.SelectableListItem("Settings")
        urwid.connect_signal(m_settings, "click", self._on_settings)
        m_shutdown = widget.SelectableListItem("Shut down")
        menu = urwid.Pile([m_apps, m_settings, urwid.Divider(), m_shutdown])

        view = urwid.Filler(
            urwid.Pile(
                [
                    logo,
                    # urwid.Text(self._get_version(), align=urwid.CENTER),
                    urwid.Padding(
                        urwid.LineBox(menu, "Main Menu", title_align="left"),
                        width=("relative", 80),
                        align=urwid.CENTER,
                    ),
                ]
            ),
            "middle",
        )
        return view

    def _on_settings(self, w: urwid.Widget) -> None:
        settings_act = SettingsActivity(self.shell)
        self.shell.screen.push_activity(settings_act)

    def _on_apps(self, w: urwid.Widget) -> None:
        apps_act = AppsActivity(self.shell)
        self.shell.screen.push_activity(apps_act)

    def activate(self) -> None:
        pass

    def destroy(self) -> None:
        pass
