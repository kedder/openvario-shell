import asyncio
from datetime import datetime

import mock
import pytest

from ovshell import api, testing
from ovshell_core import gpstime


@pytest.mark.asyncio
async def test_clock_indicator(
    ovshell: testing.OpenVarioShellStub, monkeypatch
) -> None:
    # GIVEN
    datetime_mock = mock.Mock()
    datetime_mock.utcnow.return_value = datetime(2020, 6, 2, 12, 32, 54)
    monkeypatch.setattr("ovshell_core.gpstime.datetime", datetime_mock)
    monkeypatch.setattr("ovshell_core.gpstime.CLOCK_POLL_INTERVAL", 0.01)
    state = gpstime.GPSTimeState()

    # WHEN
    task = asyncio.create_task(gpstime.clock_indicator(ovshell.screen, state))
    await asyncio.sleep(0)

    clockind = ovshell.screen.stub_get_indicator("clock")
    assert clockind is not None
    assert clockind.markup == ("ind error", "12:32 UTC")
    assert clockind.location == api.IndicatorLocation.LEFT

    state.acquired = True
    await asyncio.sleep(0.02)
    clockind = ovshell.screen.stub_get_indicator("clock")
    assert clockind is not None
    assert clockind.markup == ("ind normal", "12:32 UTC")
    assert clockind.location == api.IndicatorLocation.LEFT

    task.cancel()


@pytest.mark.asyncio
async def test_gps_time_sync(ovshell: testing.OpenVarioShellStub, monkeypatch) -> None:
    # GIVEN
    subpr_mock = mock.Mock()
    monkeypatch.setattr("ovshell_core.gpstime.subprocess", subpr_mock)

    gprmc_fields = "225446,A,4916.45,N,12311.12,W,000.5,054.7,191194,020.3"
    ovshell.devices.stub_add_nmea(
        [
            api.NMEA("", "", "ZZZ", []),
            api.NMEA("", "", "GPRMC", gprmc_fields.split(",")),
            api.NMEA("", "", "AAA", []),
        ]
    )
    state = gpstime.GPSTimeState()

    # WHEN
    await gpstime.gps_time_sync(ovshell, state)

    # THEN
    assert state.acquired is True
    datebin = ovshell.os.path("//bin/date")
    subpr_mock.run.assert_called_with(
        [datebin, "+%F %H:%M:%S", "-s", "1994-11-19 22:54:46"],
        check=True,
        capture_output=True,
    )


def test_parse_gps_datetime_correct() -> None:
    # GIVEN
    gprmc_fields = "225446,A,4916.45,N,12311.12,W,000.5,054.7,191103,020.3"
    nmea = api.NMEA("", "", "GPRMC", gprmc_fields.split(","))

    # WHEN
    dt = gpstime.parse_gps_datetime(nmea)

    # THEN
    assert dt == datetime(2003, 11, 19, 22, 54, 46)


def test_parse_gps_datetime_longtime() -> None:
    gprmc_fields = "121931.00,A,4801.86153,N,01056.69289,E,53.587,8.64,270520,,,A"
    nmea = api.NMEA("", "", "GPRMC", gprmc_fields.split(","))

    # WHEN
    dt = gpstime.parse_gps_datetime(nmea)

    # THEN
    assert dt == datetime(2020, 5, 27, 12, 19, 31)


def test_parse_gps_datetime_bad_sentence() -> None:
    # GIVEN
    gprmc_fields = "225446,A,4916.45,N,12311.12,W,000.5,054.7,191194,020.3"
    nmea = api.NMEA("", "", "XXXXX", gprmc_fields.split(","))

    # WHEN
    dt = gpstime.parse_gps_datetime(nmea)

    # THEN
    assert dt is None


def test_parse_gps_datetime_notime() -> None:
    # GIVEN
    gprmc_fields = ",,,,,,,,,"
    nmea = api.NMEA("", "", "GPRMC", gprmc_fields.split(","))

    # WHEN
    dt = gpstime.parse_gps_datetime(nmea)

    # THEN
    assert dt is None


def test_set_system_time_tolerable_offset() -> None:
    newtime = datetime(2020, 5, 29, 1, 1, 2)
    now = datetime(2020, 5, 29, 1, 1, 1)
    assert gpstime.set_system_time(newtime, now) is False


def test_set_system_time_now(monkeypatch) -> None:
    # GIVEN
    subpr_mock = mock.Mock()
    monkeypatch.setattr("ovshell_core.gpstime.subprocess", subpr_mock)
    newtime = datetime(2003, 5, 29, 1, 1, 1)

    # WHEN, THEN
    assert gpstime.set_system_time(newtime) is True
    subpr_mock.run.assert_called_with(
        ["date", "+%F %H:%M:%S", "-s", "2003-05-29 01:01:01"],
        check=True,
        capture_output=True,
    )
