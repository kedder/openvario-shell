from pathlib import Path
from typing import Generator
import asyncio

import pytest

from ovshell import testing


@pytest.fixture()
def ovshell(
    tmp_path: Path, event_loop
) -> Generator[testing.OpenVarioShellStub, None, None]:
    ovshell = testing.OpenVarioShellStub(str(tmp_path))
    yield ovshell
    ovshell.stub_teardown()
    event_loop.run_until_complete(asyncio.sleep(0))
