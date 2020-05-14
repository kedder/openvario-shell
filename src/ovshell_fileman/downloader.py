from typing import List
import os
import asyncio

from .api import ProgressState, Downloader, DownloadFilter, FileInfo


class DownloaderImpl(Downloader):
    """Object that handles file copying and listing"""

    def __init__(self, source_dir: str, mount_dir: str) -> None:
        self.source_dir = source_dir
        self.mount_dir = mount_dir

    def list_logs(self, filter: DownloadFilter) -> List[FileInfo]:
        if not os.path.exists(self.source_dir):
            return []
        downloaded = self._find_downloaded()
        res = []
        for entry in os.scandir(self.source_dir):
            _, fext = os.path.splitext(entry.name.lower())
            fileinfo = FileInfo(
                name=entry.name,
                ftype=fext,
                size=entry.stat().st_size,
                mtime=entry.stat().st_mtime,
                downloaded=entry.name.lower() in downloaded,
            )
            if self._matches(fileinfo, filter):
                res.append(fileinfo)
        return sorted(res, key=lambda fi: fi.mtime, reverse=True)

    async def download(self, file: FileInfo, progress: ProgressState) -> None:
        destdir = self._ensure_dest_dir()
        srcfile = os.path.join(self.source_dir, file.name)
        dstfile = os.path.join(destdir, file.name)

        # Copying large files can take a long time and the process can fail at
        # any time. To avoid leaving incompletely downloaded file, we copy
        # contents into temporary file, and rename it after copy completed.
        tmpdstfile = dstfile + ".partial"
        chunksize = 1024 * 4

        progress.set_total(file.size)
        with open(srcfile, "rb") as sf, open(tmpdstfile, "wb") as df:
            while True:
                chunk = sf.read(chunksize)
                if len(chunk) == 0:
                    break
                df.write(chunk)
                progress.progress(len(chunk))
                await asyncio.sleep(0)

        # Finally, rename the file
        os.replace(tmpdstfile, dstfile)

    def _matches(self, fileinfo: FileInfo, filter: DownloadFilter) -> bool:
        ftypes = [".nmea" if filter.nmea else None, ".igc" if filter.igc else None]
        matches = fileinfo.ftype in ftypes
        if filter.new:
            matches = matches and not fileinfo.downloaded
        return matches

    def _find_downloaded(self) -> List[str]:
        destdir = self._get_dest_dir()
        if not os.path.exists(destdir):
            return []

        return [fn.lower() for fn in os.listdir(destdir)]

    def _ensure_dest_dir(self) -> str:
        assert os.path.exists(self.mount_dir)
        destdir = self._get_dest_dir()
        os.makedirs(destdir, exist_ok=True)
        return destdir

    def _get_dest_dir(self) -> str:
        return os.path.join(self.mount_dir, "openvario", "igc")
