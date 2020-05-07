from typing import Generator
import asyncio

import pytest

from ovshell import testing


@pytest.fixture()
def ovshell(tmp_path, event_loop) -> Generator[testing.OpenVarioShellStub, None, None]:
    ovshell = testing.OpenVarioShellStub(tmp_path)
    yield ovshell
    ovshell.stub_teardown()
    event_loop.run_until_complete(asyncio.sleep(0))
