from ovshell.device import nmea_checksum, format_nmea, is_nmea_valid


def test_nmea_checksum() -> None:
    assert nmea_checksum("PGRMZ,+51.1,m,3") == "10"
    assert nmea_checksum("PFLAU,0,0,0,1,0,,0,,,") == "4F"


def test_format_nmea() -> None:
    assert format_nmea("PGRMZ,+51.1,m,3") == "$PGRMZ,+51.1,m,3*10"
    assert format_nmea("PFLAU,0,0,0,1,0,,0,,,") == "$PFLAU,0,0,0,1,0,,0,,,*4F"


def test_is_nmea_valid() -> None:
    assert is_nmea_valid("$PGRMZ,+51.1,m,3*10")
    assert not is_nmea_valid("PGRMZ,+51.1,m,3*10")
    assert not is_nmea_valid("$PGRMZ,+51.1,m,3")
    assert not is_nmea_valid("$PGRMZ,+51.1,m,3*11")
