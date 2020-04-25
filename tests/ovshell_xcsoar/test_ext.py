import os

from ovshell_xcsoar.ext import XCSoarProfile

SAMPLE_PROFILE = """
FriendsYellow="26CC5B,2CD854,"
DisplayOrientation="0"
HapticFeedback="1"
"""


def test_xcsoarprofile_simple_set(tmp_path) -> None:
    # GIVEN
    prf_fname = os.path.join(tmp_path, "default.prf")
    with open(os.path.join(prf_fname), "w") as f:
        f.write(SAMPLE_PROFILE)

    prf = XCSoarProfile(prf_fname)

    # WHEN
    prf.set_orientation("3")
    prf.save()

    # THEN
    with open(os.path.join(prf_fname), "r") as f:
        newconf = f.read()

    assert 'DisplayOrientation="0"' not in newconf
    assert 'DisplayOrientation="3"' in newconf
    assert len(newconf.split("\n")) == len(SAMPLE_PROFILE.split("\n"))


def test_xcsoarprofile_empty_profile(tmp_path) -> None:
    # GIVEN
    prf_fname = os.path.join(tmp_path, "default.prf")
    with open(os.path.join(prf_fname), "w") as f:
        f.write("")

    prf = XCSoarProfile(prf_fname)

    # WHEN
    prf.set_orientation("3")
    prf.save()

    # THEN
    with open(os.path.join(prf_fname), "r") as f:
        newconf = f.read()

    assert 'DisplayOrientation="3"' in newconf
    assert len(newconf.split("\n")) == 2
