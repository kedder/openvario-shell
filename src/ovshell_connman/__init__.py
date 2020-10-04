from ovshell import api
from ovshell_connman import ext


def extension(id: str, shell: api.OpenVarioShell) -> api.Extension:
    return ext.ConnmanExtension(id, shell)
