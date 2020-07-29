from ovshell import api
from ovshell_core import ext


def extension(id: str, app: api.OpenVarioShell) -> api.Extension:
    return ext.CoreExtension(id, app)
