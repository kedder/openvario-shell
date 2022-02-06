from ovshell import api

from .mailapp import GoogleMailerApp


class GoogleExtension(api.Extension):
    title = "Google"

    def __init__(self, id: str, shell: api.OpenVarioShell):
        self.id = id
        self.shell = shell

    def list_apps(self) -> list[api.App]:
        return [GoogleMailerApp(self.shell)]
