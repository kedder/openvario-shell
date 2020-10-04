from typing import Optional, Dict
import os
import asyncio

import urwid

from ovshell import api
from ovshell import widget


class ConnmanManagerApp(api.App):
    name = "connman-manager"
    title = "Networking"
    description = "Set up WiFi and other network connections"
    priority = 30

    def __init__(self, shell: api.OpenVarioShell):
        self.shell = shell

    def launch(self) -> None:
        pass
