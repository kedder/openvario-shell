from pathlib import Path

import pytest

from ovshell_fileman.api import RsyncFailedException
from ovshell_fileman.rsync import RsyncRunnerImpl, parse_rsync_line

RSYNC_STUB_SCRIPT_SUCCESS = """#!/bin/sh
echo -n "              0   0%    0.00kB/s    0:00:00 (xfr#0, ir-chk=1006/1007) \r"
echo -n "    345,081,147  13%  298.34MB/s    0:00:01 (xfr#5, ir-chk=1297/1636) \r"
echo -n "    879,293,491  33%  272.43MB/s    0:00:03 (xfr#14, ir-chk=1288/1636) \r"
"""

RSYNC_STUB_SCRIPT_ERROR = """#!/bin/sh
echo -n "              0   0%    0.00kB/s    0:00:00 (xfr#0, ir-chk=1006/1007) \r"
echo -n "    345,081,147  13%  298.34MB/s    0:00:01 (xfr#5, ir-chk=1297/1636) \r"
>&2 echo "rsync has failed"
exit 42
"""

RSYNC_STUB_SCRIPT_NO_PROGRESS = """#!/bin/sh
echo "Rsync output doesn't contain progress"
"""


class TestRsyncRunnerImpl:
    @pytest.mark.asyncio
    async def test_run_success(self, tmp_path: Path) -> None:
        # GIVEN
        rsync_path = tmp_path / "rsync-stub"
        with open(rsync_path, "w") as f:
            f.write(RSYNC_STUB_SCRIPT_SUCCESS)

        # make the script executable
        rsync_path.chmod(0o755)

        rr = RsyncRunnerImpl(str(rsync_path))

        # WHEN
        progress = []
        async for line in rr.run([]):
            progress.append(line)

        # THEN
        assert len(progress) == 3

    @pytest.mark.asyncio
    async def test_run_error(self, tmp_path: Path) -> None:
        # GIVEN
        rsync_path = tmp_path / "rsync-stub"
        with open(rsync_path, "w") as f:
            f.write(RSYNC_STUB_SCRIPT_ERROR)

        # make the script executable
        rsync_path.chmod(0o755)

        rr = RsyncRunnerImpl(str(rsync_path))

        # WHEN
        progress = []
        with pytest.raises(RsyncFailedException) as einfo:
            async for line in rr.run([]):
                progress.append(line)

        # THEN
        assert len(progress) == 2

        exc = einfo.value
        assert exc.returncode == 42
        assert exc.errors == "rsync has failed\n"

    @pytest.mark.asyncio
    async def test_run_no_progress(self, tmp_path: Path) -> None:
        # GIVEN
        rsync_path = tmp_path / "rsync-stub"
        with open(rsync_path, "w") as f:
            f.write(RSYNC_STUB_SCRIPT_NO_PROGRESS)
            for _ in range(2000):
                f.write("echo Long line without marker character\n")

        # make the script executable
        rsync_path.chmod(0o755)

        rr = RsyncRunnerImpl(str(rsync_path))

        # WHEN
        progress = []
        async for line in rr.run([]):
            progress.append(line)

        # THEN
        assert len(progress) == 0


def test_parse_rsync_line_malformed() -> None:
    # GIVEN
    line = b"               \r"

    # WHEN
    sl = parse_rsync_line(line)

    # THEN
    assert sl is None


def test_parse_rsync_line1() -> None:
    # GIVEN
    line = b"              0   0%    0.00kB/s    0:00:00 (xfr#0, ir-chk=1006/1007) \r"

    # WHEN
    sl = parse_rsync_line(line)

    # THEN
    assert sl is not None
    assert sl.transferred == 0
    assert sl.progress == 0
    assert sl.rate == "0.00kB/s"
    assert sl.elapsed == "0:00:00"
    assert sl.xfr == "xfr#0, ir-chk=1006/1007"


def test_parse_rsync_line2() -> None:
    # GIVEN
    line = b"  1,112,343,559  42%  265.39MB/s    0:00:05   \r"

    # WHEN
    sl = parse_rsync_line(line)

    # THEN
    assert sl is not None
    assert sl.transferred == 1112343559
    assert sl.progress == 42
    assert sl.rate == "265.39MB/s"
    assert sl.elapsed == "0:00:05"
    assert sl.xfr is None
