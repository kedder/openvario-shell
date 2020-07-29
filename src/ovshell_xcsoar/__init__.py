from ovshell import api
from ovshell_xcsoar import ext


def extension(id: str, shell: api.OpenVarioShell) -> api.Extension:
    return ext.XCSoarExtension(id, shell)
