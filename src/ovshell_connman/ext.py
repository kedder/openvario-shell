from typing import Sequence

from ovshell import api
from ovshell_connman import app


class ConnmanExtension(api.Extension):
    title = "Connman"

    def __init__(self, id: str, shell: api.OpenVarioShell):
        self.id = id
        self.shell = shell

    def list_apps(self) -> Sequence[api.App]:
        return [app.ConnmanManagerApp(self.shell)]
