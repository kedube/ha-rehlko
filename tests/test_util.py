"""Formatting/parsing helpers and the recovered enum vocabulary."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from custom_components.rehlko_energy.api import vocabulary as V
from custom_components.rehlko_energy.api.util import (
    device_mac,
    format_timestamp,
    has_offset,
    humanize,
    magnitude,
    parse_timestamp,
    plain_ip,
    slugify,
)


def test_humanize_keeps_acronyms() -> None:
    assert humanize("LowOilPressureWarning") == "Low oil pressure warning"
    assert humanize("AtsExerciseActive") == "ATS exercise active"
    assert humanize("EcmPowered") == "ECM powered"
    assert humanize(None) is None
    assert humanize("already spaced") == "Already spaced"


def test_slugify() -> None:
    assert slugify("EveryOtherWeek") == "every_other_week"
    assert slugify("UnloadedFullSpeed") == "unloaded_full_speed"
    assert slugify("REC") == "rec"


def test_parse_timestamp_variants() -> None:
    assert parse_timestamp("2026-11-12T20:00:00Z").hour == 20
    assert parse_timestamp("2026-11-12T20:00:00.7399592+00:00").tzinfo is not None
    assert parse_timestamp("0001-01-01T00:00:00") is None
    assert parse_timestamp("") is None
    assert parse_timestamp(None) is None


def test_parse_timestamp_naive_gets_default_tz() -> None:
    tz = UTC
    parsed = parse_timestamp("2026-11-12T20:00:00", tz)
    assert parsed.tzinfo is tz


def test_has_offset() -> None:
    assert has_offset("2026-11-12T20:00:00Z") is True
    assert has_offset("2026-11-12T20:00:00+00:00") is True
    assert has_offset("2026-11-12T20:00:00") is False
    assert has_offset("not a date") is None


def test_format_timestamp_mirrors_source_form() -> None:
    when = datetime(2026, 11, 12, 20, 0, tzinfo=UTC)
    # When the service used an offset form, write one.
    assert "+00:00" in format_timestamp(when, like="2026-01-01T00:00:00Z")
    # When the service used a naive wall-clock, write naive local time (no offset).
    naive = format_timestamp(when, like="2026-01-01T00:00:00", site_tz=UTC)
    assert naive == "2026-11-12T20:00:00"


@pytest.mark.parametrize(
    ("reported", "address"),
    [
        # What the service sends: the socket it saw, an IPv4 peer written the IPv6 way.
        ("[::ffff:100.100.0.69]:42636", "100.100.0.69"),
        ("[::ffff:6464:45]:42636", "100.100.0.69"),
        ("::ffff:100.100.0.69", "100.100.0.69"),
        ("100.100.0.69:42636", "100.100.0.69"),
        ("100.100.0.69", "100.100.0.69"),
        (" 100.100.0.69 ", "100.100.0.69"),
        # A real IPv6 address stays IPv6, and its last group is not taken for a port.
        ("[2001:db8::1]:443", "2001:db8::1"),
        ("[2001:db8::1]", "2001:db8::1"),
        ("2001:db8::8a2e:370:7334", "2001:db8::8a2e:370:7334"),
        ("2001:0db8:0000:0000:0000:0000:0000:0001", "2001:db8::1"),
        # Not an address: shown as reported, not dropped.
        ("gateway.example:443", "gateway.example:443"),
        ("[not an address]:1", "[not an address]:1"),
        ("", None),
        ("   ", None),
        (None, None),
    ],
)
def test_plain_ip_takes_the_address_out_of_a_socket(reported, address) -> None:
    assert plain_ip(reported) == address


@pytest.mark.parametrize(
    ("reported", "address"),
    [
        # The service sends the bytes back to front; Home Assistant's own integration turns
        # them round too (its test fixture is the first of these).
        ("91:E1:20:63:10:00", "00:10:63:20:E1:91"),
        ("aa-bb-cc-dd-ee-ff", "ff:ee:dd:cc:bb:aa"),
        (" 01:02:03:04:05:06 ", "06:05:04:03:02:01"),
        # Not six bytes: shown as reported.
        ("0102.0304.0506", "0102.0304.0506"),
        ("01:02:03:04:05", "01:02:03:04:05"),
        ("zz:02:03:04:05:06", "zz:02:03:04:05:06"),
        ("", None),
        (None, None),
    ],
)
def test_device_mac_is_put_in_network_order(reported, address) -> None:
    assert device_mac(reported) == address


def test_magnitude_drops_the_sign_and_keeps_missing_readings_missing() -> None:
    assert magnitude(-5400) == 5400
    assert magnitude("-12.5") == 12.5
    assert magnitude(0) == 0
    assert magnitude(None) is None
    assert magnitude("n/a") is None
    assert magnitude(True) is None


def test_vocabulary_shapes() -> None:
    assert "ReadyToRun" in V.DEVICE_STATUS and "Offline" in V.DEVICE_STATUS
    assert V.EXERCISE_MODE[:2] == ("None", "Unloaded")
    assert V.EXERCISE_FREQUENCY == ("Weekly", "EveryOtherWeek", "Monthly")
    assert "Generator" in V.POWER_SOURCE
    assert len(V.DEVICE_EVENT_ID) > 300  # the full fault catalogue
    # Every value is a non-empty string.
    for name in dir(V):
        if name.isupper():
            values = getattr(V, name)
            assert all(isinstance(v, str) and v for v in values), name
