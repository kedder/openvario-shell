import sys
import argparse
import asyncio

import urwid

parser = argparse.ArgumentParser(description="Shell for Openvario")


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


def startui(urwidloop) -> None:
    pass


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
        ("screen header", "yellow", "black", ""),
        ("bg", "light gray", "black", ""),
        ("success message", "light green", "black", ""),
        ("success banner", "white", "dark green", ""),
        ("error message", "light red", "black", ""),
        ("error banner", "white", "dark red", ""),
        ("progress", "light magenta", "black", ""),
        ("remark", "dark gray", "black", ""),
    ]

    btxt = urwid.BigText("Openvario", urwid.font.Thin6x6Font())
    splash = urwid.Filler(urwid.Padding(btxt, "center", "clip"), "middle")

    asyncioloop = asyncio.get_event_loop()
    evl = urwid.AsyncioEventLoop(loop=asyncioloop)

    urwidloop = urwid.MainLoop(
        splash, palette=palette, event_loop=evl, input_filter=debounce_esc
    )

    asyncioloop.call_soon(startui, urwidloop)

    try:
        urwidloop.run()
    except KeyboardInterrupt:
        pass


def main():
    run(sys.argv[1:])
