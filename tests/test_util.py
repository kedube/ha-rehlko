"""Formatting/parsing helpers and the recovered enum vocabulary."""

from __future__ import annotations

from datetime import UTC, datetime

from custom_components.rehlko_energy.api import vocabulary as V
from custom_components.rehlko_energy.api.util import (
    format_timestamp,
    has_offset,
    humanize,
    parse_timestamp,
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
