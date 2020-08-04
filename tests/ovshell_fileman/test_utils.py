from ovshell_fileman.utils import format_size


def test_storedfile_format_size() -> None:
    assert format_size(1024) == "1.0 KiB"
    assert format_size(1) == "1.0 B  "
    assert format_size(100000) == "97.7 KiB"
    assert format_size(10000000) == "9.5 MiB"
    assert format_size(2 ** 32) == "4.0 GiB"
    assert format_size(2 ** 48) == "256.0 TiB"
