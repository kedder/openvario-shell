from ovshell import protocol


class CoreExtension(protocol.Extension):
    title = "Core"

    def __init__(self, id: str, app: protocol.OpenVarioShell):
        self.id = id
        self.app = app


def extension(id: str, app: protocol.OpenVarioShell) -> protocol.Extension:
    return CoreExtension(id, app)
