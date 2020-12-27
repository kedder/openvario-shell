from typing import Sequence

from ovshell import api
from ovshell_connman import app

from .agent import ConnmanAgentImpl
from .agentiface import ConnmanAgentInterface
from .indicator import start_indicator


class ConnmanExtension(api.Extension):
    title = "Connman"

    def __init__(self, id: str, shell: api.OpenVarioShell):
        self.id = id
        self.shell = shell

    def list_apps(self) -> Sequence[api.App]:
        return [app.ConnmanManagerApp(self.shell)]

    def start(self) -> None:
        self.shell.processes.start(start_services(self.shell))


async def start_services(shell: api.OpenVarioShell) -> None:
    try:
        bus = await shell.os.get_system_bus()
    except api.DBusNotAvailableException:
        # Cannot connect to dbus, ignore
        shell.screen.set_status(("error message", "Cannot connect to D-BUS service"))
        return

    agent = ConnmanAgentImpl(shell.screen)
    iface = ConnmanAgentInterface(agent, bus)
    shell.processes.start(iface.register())

    shell.processes.start(start_indicator(shell.screen, bus))
