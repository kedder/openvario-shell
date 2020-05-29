import urwid

from ovshell import protocol
from ovshell import widget


class SystemUpgradeApp(protocol.App):
    name = "system-upgrade"
    title = "Update"
    description = "Check for system updates"
    priority = 20

    def __init__(self, shell: protocol.OpenVarioShell):
        self.shell = shell

    def launch(self) -> None:
        act = SystemUpgradeActivity(self.shell)
        self.shell.screen.push_activity(act)


class SystemUpgradeActivity(protocol.Activity):
    def __init__(self, shell: protocol.OpenVarioShell) -> None:
        self.shell = shell

    def create(self) -> urwid.Widget:
        intro = urwid.Filler(urwid.Text("System updates", align="center"), "middle")
        self.frame = urwid.Frame(intro, header=widget.ActivityHeader("System update"))
        return self.frame
