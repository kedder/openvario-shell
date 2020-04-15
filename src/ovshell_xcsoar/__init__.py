from ovshell import protocol
from ovshell_xcsoar import ext


def extension(id: str, shell: protocol.OpenVarioShell) -> protocol.Extension:
    return ext.XCSoarExtension(id, shell)
