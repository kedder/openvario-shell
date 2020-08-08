from typing import List, Optional, Coroutine, AsyncGenerator
from typing_extensions import Protocol
import re
import asyncio
from dataclasses import dataclass
from abc import abstractmethod

from ovshell_fileman.api import RsyncRunner, RsyncFailedException, RsyncStatusLine

RSYNC_PROGRESS2_RE = r"([\d,]+)\s+(\d+)%\s+([\d\.]+.B\/s)\s+([\d:]+)(\s+\((.*)\))?"


class RsyncRunnerImpl(RsyncRunner):
    def __init__(self, rsync_path: str) -> None:
        self.rsync_path = rsync_path

    async def run(self, params: List[str]) -> AsyncGenerator[RsyncStatusLine, None]:
        proc = await asyncio.create_subprocess_exec(
            self.rsync_path,
            "--info=progress2",
            *params,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            limit=200,
        )

        assert proc.stdout is not None
        assert proc.stderr is not None

        while not proc.stdout.at_eof():
            try:
                line = await proc.stdout.readuntil(b"\r")
            except asyncio.IncompleteReadError:
                break
            rsync_progress = parse_rsync_line(line)
            if rsync_progress is not None:
                yield rsync_progress

        result = await proc.wait()
        if result != 0:
            errors = await proc.stderr.read()
            raise RsyncFailedException(result, errors.decode())


def parse_rsync_line(line: bytes) -> Optional[RsyncStatusLine]:
    match = re.match(RSYNC_PROGRESS2_RE, line.strip().decode())
    if match is None:
        return None

    return RsyncStatusLine(
        transferred=int(match.group(1).replace(",", "")),
        progress=int(match.group(2)),
        rate=match.group(3),
        elapsed=match.group(4),
        xfr=match.group(6),
    )
