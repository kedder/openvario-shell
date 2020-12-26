from ovshell.api import Extension, OpenVarioShell
from ovshell_connman import ext


def extension(id: str, shell: OpenVarioShell) -> Extension:
    return ext.ConnmanExtension(id, shell)
