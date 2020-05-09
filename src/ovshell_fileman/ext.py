from typing import Sequence

from ovshell import protocol

from ovshell_fileman.downloadapp import LogDownloaderApp


class FileManagerExtension(protocol.Extension):
    title = "File Management"

    def __init__(self, id: str, shell: protocol.OpenVarioShell):
        self.id = id
        self.shell = shell

    def list_apps(self) -> Sequence[protocol.App]:
        return [LogDownloaderApp(self.shell)]
