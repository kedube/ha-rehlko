"""Coordinator change-detection logic: seen-tracking, power events, bursts, event shaping.

These exercise the pure pieces without a running Home Assistant. SeenTracker's Store is
replaced with an in-memory stub so no disk or hass is needed.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from custom_components.rehlko_energy import coordinator as coord
from custom_components.rehlko_energy.coordinator import (
    POWER_GENERATOR_STARTED,
    POWER_GENERATOR_STOPPED,
    POWER_TO_GENERATOR,
    POWER_UTILITY_LOST,
    POWER_UTILITY_RESTORED,
    SeenTracker,
    describe_event,
    describe_notification,
    item_key,
)
from custom_components.rehlko_energy.models import GeneratorData


@pytest.fixture
def tracker(monkeypatch) -> SeenTracker:
    class MemStore:
        def __init__(self, *a, **k) -> None:
            self.data = None

        def async_delay_save(self, fn, _delay) -> None:
            self.data = fn()

        async def async_load(self):
            return self.data

        async def async_remove(self) -> None:
            self.data = None

    monkeypatch.setattr(coord, "Store", MemStore)
    return SeenTracker(SimpleNamespace(), "entry-1")


def gen(**kw) -> GeneratorData:
    return GeneratorData(
        device_id=1,
        home={},
        device=kw.get("device", {}),
        details=kw.get("details", {}),
        alerts=kw.get("alerts", []),
    )


def test_item_key_prefers_id() -> None:
    assert item_key({"id": 5}) == "5"
    assert item_key({"deviceEventId": "OverCrank", "timestamp": "t"}) == "OverCrank|t"


def test_fresh_seeds_then_detects_new(tracker: SeenTracker) -> None:
    first = [{"id": 1}, {"id": 2}]
    # First sight only seeds — nothing is "new".
    assert tracker.fresh(1, "events", first) == []
    # A later poll with one extra item reports just that item.
    assert tracker.fresh(1, "events", [{"id": 3}, {"id": 1}, {"id": 2}]) == [{"id": 3}]
    # Re-seeing the same set reports nothing.
    assert tracker.fresh(1, "events", [{"id": 3}, {"id": 1}, {"id": 2}]) == []


def test_active_diff_reports_added_and_cleared(tracker: SeenTracker) -> None:
    assert tracker.active_diff(1, "alerts", [{"id": 1}]) == ([], [])  # seed
    added, cleared = tracker.active_diff(1, "alerts", [{"id": 1}, {"id": 2}])
    assert [a["id"] for a in added] == [2] and cleared == []
    added, cleared = tracker.active_diff(1, "alerts", [{"id": 2}])
    assert added == [] and cleared == ["1"]


def test_power_changes_detects_outage_and_transfer() -> None:
    old = gen(
        details={
            "utilityVoltageV": 241,
            "setOutputVoltageV": 240,
            "powerSource": "Utility",
            "engineState": "Off",
        }
    )
    new = gen(
        device={"status": "Running"},
        details={
            "utilityVoltageV": 0,
            "setOutputVoltageV": 240,
            "powerSource": "Generator",
            "engineState": "Running",
            "engineSpeedRpm": 1800,
        },
    )
    kinds = {i.event_type for i in coord.RehlkoCoordinator._power_changes(old, new)}
    assert POWER_UTILITY_LOST in kinds
    assert POWER_GENERATOR_STARTED in kinds
    assert POWER_TO_GENERATOR in kinds


def test_power_changes_detects_restore_and_stop() -> None:
    old = gen(
        device={"status": "Running"},
        details={
            "utilityVoltageV": 0,
            "setOutputVoltageV": 240,
            "powerSource": "Generator",
            "engineSpeedRpm": 1800,
        },
    )
    new = gen(
        details={
            "utilityVoltageV": 241,
            "setOutputVoltageV": 240,
            "powerSource": "Utility",
            "engineState": "Off",
            "engineSpeedRpm": 0,
        }
    )
    kinds = {i.event_type for i in coord.RehlkoCoordinator._power_changes(old, new)}
    assert POWER_UTILITY_RESTORED in kinds
    assert POWER_GENERATOR_STOPPED in kinds


def test_power_changes_quiet_when_unchanged() -> None:
    same = dict(
        utilityVoltageV=241, setOutputVoltageV=240, powerSource="Utility", engineState="Off"
    )
    assert coord.RehlkoCoordinator._power_changes(gen(details=same), gen(details=dict(same))) == []


def test_burst_clamps_to_newest() -> None:
    items = [{"id": i, "timestamp": f"2026-11-12T00:00:{i:02d}Z"} for i in range(40)]
    out = coord.RehlkoCoordinator._burst(items)
    assert len(out) == coord.MAX_BURST
    assert out[-1]["id"] == 39  # newest kept


def test_describe_event_flattens_fields() -> None:
    d = describe_event(
        {
            "id": 1,
            "deviceEventId": "OverCrank",
            "level": "Shutdown",
            "fmi": "High",
            "isCriticalFault": True,
            "timestamp": "t",
        }
    )
    assert d["code"] == "OverCrank"
    assert d["name"] == "Over crank"
    assert d["is_critical_fault"] is True


def test_describe_notification_flattens_fields() -> None:
    d = describe_notification(
        {
            "id": 2,
            "type": "EngineStartedNotice",
            "message": "started",
            "ctaLink": "x",
            "isEStopEvent": False,
        }
    )
    assert d["notification_type"] == "EngineStartedNotice"
    assert d["message"] == "started"
    assert d["cta_link"] == "x"


async def test_seen_tracker_roundtrip(tracker: SeenTracker) -> None:
    tracker.fresh(1, "events", [{"id": 1}])
    await tracker.async_load()  # does not raise with the stub
    await tracker.async_remove()


def test_long_feed_does_not_reannounce_evicted_history(tracker: SeenTracker) -> None:
    from datetime import UTC, datetime, timedelta

    start = datetime(2026, 1, 1, tzinfo=UTC)
    items = [{"id": i, "timestamp": (start + timedelta(minutes=i)).isoformat()} for i in range(600)]
    assert tracker.fresh(1, "events", items) == []
    assert tracker.fresh(1, "events", list(reversed(items))) == []
    newest = {"id": 600, "timestamp": (start + timedelta(minutes=600)).isoformat()}
    assert tracker.fresh(1, "events", [*items, newest]) == [newest]
    assert tracker.fresh(1, "events", [*items, newest]) == []
