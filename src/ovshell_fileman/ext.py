from typing import Sequence

from ovshell import api
from ovshell_fileman.backupapp import BackupRestoreApp
from ovshell_fileman.downloadapp import LogDownloaderApp


class FileManagerExtension(api.Extension):
    title = "File Management"

    def __init__(self, id: str, shell: api.OpenVarioShell):
        self.id = id
        self.shell = shell

    def list_apps(self) -> Sequence[api.App]:
        return [LogDownloaderApp(self.shell), BackupRestoreApp(self.shell)]
