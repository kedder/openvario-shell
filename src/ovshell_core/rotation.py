import os
import re
from typing import List, Tuple

from ovshell import api


def get_rotations() -> List[Tuple[str, str]]:
    return [
        ("0", "Landscape"),
        ("1", "Portrait (90°)"),
        ("2", "Landscape (180°)"),
        ("3", "Portrait (270°)"),
    ]


def apply_rotation(ovos: api.OpenVarioOS, rotation: str) -> None:

    uenvconf_fname = ovos.path("//boot/config.uEnv")
    if not os.path.exists(uenvconf_fname):
        ovos.mount_boot()

    with open(uenvconf_fname, "r") as f:
        uenvconf = f.read()

    uenvconf = re.sub(r"rotation=[0-3]", "rotation=" + rotation, uenvconf)

    with open(uenvconf_fname, "w") as f:
        f.write(uenvconf)

    # For some weird reason 90 degree rotation is inverted for fbcon
    fbcon_rotmap = {
        "0": "0",  # normal
        "1": "3",  # portrait (90)
        "2": "2",  # landscape (180)
        "3": "1",  # portrait (270)
    }
    with open(ovos.path("//sys/class/graphics/fbcon/rotate_all"), "w") as f:
        f.write(fbcon_rotmap[rotation])
