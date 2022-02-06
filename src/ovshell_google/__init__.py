from ovshell.api import OpenVarioShell, Extension
from ovshell_google import ext


def extension(id: str, shell: OpenVarioShell) -> Extension:
    return ext.GoogleExtension(id, shell)
