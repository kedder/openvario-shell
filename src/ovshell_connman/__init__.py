from ovshell.api import OpenVarioShell, Extension
from ovshell_connman import ext


def extension(id: str, shell: OpenVarioShell) -> Extension:
    return ext.ConnmanExtension(id, shell)
