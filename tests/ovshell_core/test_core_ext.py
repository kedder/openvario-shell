from ovshell import testing

import ovshell_core


def test_extension(ovshell: testing.OpenVarioShellStub) -> None:
    ext = ovshell_core.extension("core", ovshell)
    assert ext is not None

    # Check settings initialization
    settings = ext.list_settings()
    assert len(settings) == 6

    # Basic settings are initialized
    assert ovshell.settings.getstrict("core.screen_orientation", str) == "0"
    assert ovshell.settings.getstrict("core.language", str) == "en_EN.UTF-8"
