from datetime import datetime

import mock
import pytest

from ovshell import protocol
from ovshell import testing
from ovshell_core import gpstime


@pytest.mark.asyncio
async def test_gps_time_sync(ovshell: testing.OpenVarioShellStub, monkeypatch) -> None:
    # GIVEN
    subpr_mock = mock.Mock()
    monkeypatch.setattr("ovshell_core.gpstime.subprocess", subpr_mock)

    gprmc_fields = "225446,A,4916.45,N,12311.12,W,000.5,054.7,191194,020.3"
    ovshell.devices.stub_add_nmea(
        [
            protocol.NMEA("", "", "ZZZ", []),
            protocol.NMEA("", "", "GPRMC", gprmc_fields.split(",")),
            protocol.NMEA("", "", "AAA", []),
        ]
    )

    # WHEN
    await gpstime.gps_time_sync(ovshell)

    # THEN
    datebin = ovshell.os.path("//usr/bin/date")
    subpr_mock.run.assert_called_with(
        [datebin, "+%F %H:%M:%S", "-s", "1994-11-19 22:54:46"], check=True
    )


def test_parse_gps_datetime_correct() -> None:
    # GIVEN
    gprmc_fields = "225446,A,4916.45,N,12311.12,W,000.5,054.7,191103,020.3"
    nmea = protocol.NMEA("", "", "GPRMC", gprmc_fields.split(","))

    # WHEN
    dt = gpstime.parse_gps_datetime(nmea)

    # THEN
    assert dt == datetime(2003, 11, 19, 22, 54, 46)


def test_parse_gps_datetime_bad_sentence() -> None:
    # GIVEN
    gprmc_fields = "225446,A,4916.45,N,12311.12,W,000.5,054.7,191194,020.3"
    nmea = protocol.NMEA("", "", "XXXXX", gprmc_fields.split(","))

    # WHEN
    dt = gpstime.parse_gps_datetime(nmea)

    # THEN
    assert dt is None


def test_parse_gps_datetime_notime() -> None:
    # GIVEN
    gprmc_fields = ",,,,,,,,,"
    nmea = protocol.NMEA("", "", "GPRMC", gprmc_fields.split(","))

    # WHEN
    dt = gpstime.parse_gps_datetime(nmea)

    # THEN
    assert dt is None


def test_set_system_time_tolerable_offset() -> None:
    newtime = datetime(2020, 5, 29, 1, 1, 2)
    now = datetime(2020, 5, 29, 1, 1, 1)
    assert gpstime.set_system_time(newtime, now) == False


def test_set_system_time_now(monkeypatch) -> None:
    # GIVEN
    subpr_mock = mock.Mock()
    monkeypatch.setattr("ovshell_core.gpstime.subprocess", subpr_mock)
    newtime = datetime(2003, 5, 29, 1, 1, 1)

    # WHEN, THEN
    assert gpstime.set_system_time(newtime) == True
    subpr_mock.run.assert_called_with(
        ["date", "+%F %H:%M:%S", "-s", "2003-05-29 01:01:01"], check=True
    )
