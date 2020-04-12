from ovshell import protocol
from ovshell_xcsoar import ext


def extension(id: str, app: protocol.OpenVarioShell) -> protocol.Extension:
    return ext.XCSoarExtension(id, app)
