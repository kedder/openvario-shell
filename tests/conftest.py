import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncContextManager, AsyncIterator, Callable, Coroutine, Generator

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


@pytest.fixture()
def task_running() -> Callable[[Coroutine], AsyncContextManager[None]]:
    def _task_done(task) -> None:
        if task.cancelled():
            return
        exc = task.exception()
        if exc:
            pytest.fail(f"Task {task} failed: {exc}", pytrace=False)

    @asynccontextmanager
    async def runner(coro: Coroutine) -> AsyncIterator[None]:
        task = asyncio.create_task(coro)
        task.add_done_callback(_task_done)
        try:
            yield
        finally:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    return runner
