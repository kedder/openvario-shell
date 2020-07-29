"""File manager extension"""

import ovshell.api
from ovshell_fileman import ext


def extension(id: str, shell: ovshell.api.OpenVarioShell) -> ovshell.api.Extension:
    return ext.FileManagerExtension(id, shell)
