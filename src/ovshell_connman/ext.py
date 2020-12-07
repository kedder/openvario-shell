from typing import Sequence

from ovshell import api
from ovshell_connman import app

from .agent import ConnmanAgentImpl
from .agentiface import ConnmanAgentInterface


class ConnmanExtension(api.Extension):
    title = "Connman"

    def __init__(self, id: str, shell: api.OpenVarioShell):
        self.id = id
        self.shell = shell

    def list_apps(self) -> Sequence[api.App]:
        return [app.ConnmanManagerApp(self.shell)]

    def start(self) -> None:
        self.shell.processes.start(start_connman_agent(self.shell))


async def start_connman_agent(shell: api.OpenVarioShell) -> None:
    agent = ConnmanAgentImpl(shell.screen)
    try:
        bus = await shell.os.get_system_bus()
    except api.DBusNotAvailableException:
        # Cannot connect to dbus, ignore
        shell.screen.set_status(("error message", "Cannot connect to D-BUS service"))
        return
    iface = ConnmanAgentInterface(agent, bus)
    await iface.register()
