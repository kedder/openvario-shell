"""File manager extension"""

from ovshell import protocol
from ovshell_fileman import ext


def extension(id: str, shell: protocol.OpenVarioShell) -> protocol.Extension:
    return ext.FileManagerExtension(id, shell)
