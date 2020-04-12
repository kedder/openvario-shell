from ovshell import protocol
from ovshell_core import ext


def extension(id: str, app: protocol.OpenVarioShell) -> protocol.Extension:
    return ext.CoreExtension(id, app)
