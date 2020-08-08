from ovshell_fileman.rsync import parse_rsync_line


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
