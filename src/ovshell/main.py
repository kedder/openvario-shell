from typing import Tuple, Optional
import os
import sys
import argparse
import asyncio

import urwid

from ovshell import protocol
from ovshell.app import OpenvarioShellImpl
from ovshell.screen import ScreenManagerImpl
from ovshell.ui.mainmenu import MainMenuActivity

parser = argparse.ArgumentParser(description="Shell for Openvario")
parser.add_argument(
    "--config",
    default=os.environ.get("OVSHELL_CONFIG", ".ovshell.conf"),
    required=False,
    help="Use provided configuration file.",
)
parser.add_argument(
    "--sim",
    metavar="ROOTFS",
    default=os.environ.get("OVSHELL_ROOTFS"),
    required=False,
    help="Run in simulated mode (on provided root filesystem).",
)
parser.add_argument(
    "--run",
    metavar="APP",
    required=False,
    help="Run given app automatically on startup. Useful during app development",
)


def debounce_esc(keys, raw):
    # For some weird reason, SteFly remote stick sends two "Escape" key presses
    # when user presses X button once. Whatever reason might be, this is a
    # permanent deision and we have to deal with that. We still want to handle
    # single escape keypresses though, to support input devices that behave
    # sanely.
    filtered = []
    escpressed = False
    for k in keys:
        if k == "esc":
            if escpressed:
                escpressed = False
                filtered.append(k)
            else:
                escpressed = True
        else:
            if escpressed:
                filtered.append("esc")
                escpressed = False
            filtered.append(k)
    if escpressed:
        filtered.append("esc")
    return filtered


def get_autostart_app(
    shell: protocol.OpenVarioShell, args: argparse.Namespace
) -> Optional[protocol.AppInfo]:
    if args.run:
        appinfo = shell.apps.get(args.run)
        if appinfo is not None:
            return appinfo
        else:
            availapps = ", ".join([a.id for a in shell.apps.list()])
            print(
                f"Error: app '{args.run}' does not exist. Available apps: {availapps}"
            )
            sys.exit(1)
    return None


def startui(ctx: Tuple[OpenvarioShellImpl, protocol.AppInfo]) -> None:
    shell, autostart = ctx
    shell.screen.push_activity(MainMenuActivity(shell))
    if autostart is not None:
        autostart.app.launch()


def run(argv) -> None:
    args = parser.parse_args(argv)

    palette = [
        ("text", "white", "black", ""),
        ("btn focus", "white", "dark red", ""),
        ("btn normal", "white", "dark blue", ""),
        ("li normal", "light cyan", "black", ""),
        ("li focus", "white", "dark red", ""),
        ("pg normal", "white", "black", "standout"),
        ("pg complete", "white", "dark magenta"),
        ("pg smooth", "dark magenta", "black"),
        ("screen header", "white", "brown", "standout"),
        ("screen header divider", "black", "brown", ""),
        ("bg", "light gray", "black", ""),
        ("success message", "light green", "black", ""),
        ("success banner", "white", "dark green", ""),
        ("error message", "light red", "black", ""),
        ("error banner", "white", "dark red", ""),
        ("progress", "light magenta", "black", ""),
        ("remark", "dark gray", "black", ""),
        ("topbar", "black", "white", ""),
        # Light color scheme (for modals and popups)
        ("bg light", "black", "white", ""),
        ("li normal light", "dark blue", "white", ""),
    ]

    # btxt = urwid.BigText("Openvario", urwid.font.Thin6x6Font())
    # splash = urwid.Filler(urwid.Padding(btxt, "center", "clip"), "middle")

    asyncioloop = asyncio.get_event_loop()
    evl = urwid.AsyncioEventLoop(loop=asyncioloop)

    urwidloop = urwid.MainLoop(
        None, palette=palette, event_loop=evl, input_filter=debounce_esc, pop_ups=True,
    )

    screen = ScreenManagerImpl(urwidloop)

    shell = OpenvarioShellImpl(screen, config=args.config, rootfs=args.sim)
    shell.extensions.load_all(shell)
    shell.apps.install_new_apps()

    autostart = get_autostart_app(shell, args)
    asyncioloop.call_soon(startui, (shell, autostart))

    try:
        urwidloop.run()
    except KeyboardInterrupt:
        pass


def main():
    run(sys.argv[1:])
