import re

from ovshell import api


def get_rotations() -> list[tuple[str, str]]:
    return [
        ("0", "Landscape"),
        ("1", "Portrait (90°)"),
        ("2", "Landscape (180°)"),
        ("3", "Portrait (270°)"),
    ]


def apply_rotation(ovos: api.OpenVarioOS, rotation: str) -> None:

    uenvconf_fname = ovos.path("//boot/config.uEnv")

    with open(uenvconf_fname) as f:
        uenvconf = f.read()

    uenvconf = re.sub(r"rotation=[0-3]", "rotation=" + rotation, uenvconf)

    with open(uenvconf_fname, "w") as f:
        f.write(uenvconf)

    with open(ovos.path("//sys/class/graphics/fbcon/rotate_all"), "w") as f:
        f.write(rotation)
