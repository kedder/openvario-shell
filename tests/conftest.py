import pytest

from ovshell import testing


@pytest.fixture()
def ovshell(tmp_path) -> testing.OpenVarioShellStub:
    return testing.OpenVarioShellStub(tmp_path)
