from typing import List
from pathlib import Path
from unittest import mock

import pytest

from ovshell_fileman.downloader import DownloaderImpl
from ovshell_fileman.api import ProgressState, DownloadFilter, FileInfo


class ProgressStateStub(ProgressState):
    log: List[str]

    def __init__(self):
        self.log = []

    def set_total(self, total: int) -> None:
        self.log.append(f"total: {total}")

    def progress(self, amount: int = 1) -> None:
        self.log.append(f"progress: {amount}")


def test_list_logs_missingdirs(tmp_path: Path) -> None:
    # GIVEN
    dl = DownloaderImpl(str(tmp_path / "source"), str(tmp_path / "target"))
    filt = DownloadFilter()

    # WHEN
    logs = dl.list_logs(filt)

    # THEN
    assert logs == []


def test_list_logs_notarget(tmp_path: Path) -> None:
    # GIVEN
    srcdir = tmp_path / "source"
    srcdir.mkdir()
    srcdir.joinpath("one.igc").touch()
    dl = DownloaderImpl(str(srcdir), str(tmp_path / "target"))
    filt = DownloadFilter()

    # WHEN
    logs = dl.list_logs(filt)

    # THEN
    assert logs == [
        FileInfo("one.igc", ftype=".igc", size=0, mtime=mock.ANY, downloaded=False)
    ]


def test_list_logs_filtering(tmp_path: Path) -> None:
    # GIVEN
    srcdir = tmp_path / "source"
    srcdir.mkdir()
    srcdir.joinpath("one.igc").touch()
    srcdir.joinpath("two.igc").touch()

    tgtdir = tmp_path / "target"
    tgtdir.joinpath("openvario", "igc").mkdir(parents=True)
    tgtdir.joinpath("openvario", "igc", "two.igc").touch()

    dl = DownloaderImpl(str(srcdir), str(tgtdir))

    # WHEN, THEN
    logs = dl.list_logs(DownloadFilter(new=True))
    assert [l.name for l in logs] == ["one.igc"]

    # Files are listed in reverse-chronological order
    logs = dl.list_logs(DownloadFilter(new=False))
    assert [l.name for l in logs] == ["two.igc", "one.igc"]

    logs = dl.list_logs(DownloadFilter(new=True, igc=False, nmea=True))
    assert [l.name for l in logs] == []

    # Type is detected by extensions, that are case-insensitive
    srcdir.joinpath("three.NMEA").touch()
    logs = dl.list_logs(DownloadFilter(new=True, igc=False, nmea=True))
    assert [l.name for l in logs] == ["three.NMEA"]


@pytest.mark.asyncio
async def test_download(tmp_path: Path) -> None:
    # GIVEN
    srcdir = tmp_path / "source"
    srcdir.mkdir()
    srcdir.joinpath("one.igc").write_bytes(b"\0" * 10000)

    tgtdir = tmp_path / "target"
    tgtdir.mkdir()

    dl = DownloaderImpl(str(srcdir), str(tgtdir))
    progress = ProgressStateStub()
    files = dl.list_logs(DownloadFilter(igc=True))
    fileinfo = files[0]

    # WHEN
    await dl.download(fileinfo, progress)

    # THEN
    # proress is reported correctly
    progress.log == [
        "total: 10000",
        "progress: 4096",
        "progress: 4096",
        "progress: 1808",
    ]

    downloaded = tgtdir / "openvario" / "igc" / "one.igc"
    assert downloaded.parent.is_dir()
    assert downloaded.exists()
    assert downloaded.stat().st_size == 10000
