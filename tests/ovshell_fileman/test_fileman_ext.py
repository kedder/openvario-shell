from ovshell import testing

import ovshell_fileman


def test_extension(ovshell: testing.OpenVarioShellStub) -> None:
    ext = ovshell_fileman.extension("fileman", ovshell)
    assert ext is not None

    apps = ext.list_apps()
    assert len(apps) == 1
