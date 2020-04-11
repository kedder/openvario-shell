from ovshell import protocol
from ovcore import ext


def extension(id: str, app: protocol.OpenVarioShell) -> protocol.Extension:
    return ext.CoreExtension(id, app)
