import asyncio
from typing import Coroutine, Set


class ProcessManagerImpl:
    _tasks: Set[asyncio.Task]

    def __init__(self) -> None:
        self._tasks = set()

    def start(self, coro: Coroutine) -> asyncio.Task:
        task = asyncio.create_task(coro)
        task.add_done_callback(self._task_done)
        self._tasks.add(task)
        return task

    def _task_done(self, task: asyncio.Task) -> None:
        self._tasks.remove(task)
        if task.cancelled():
            return
        exc = task.exception()
        if exc is not None:
            raise exc
