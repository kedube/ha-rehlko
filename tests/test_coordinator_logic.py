"""Coordinator change-detection logic: seen-tracking, power events, bursts, event shaping.

These exercise the pure pieces without a running Home Assistant. SeenTracker's Store is
replaced with an in-memory stub so no disk or hass is needed.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Iterator
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any
from unittest.mock import patch
from zoneinfo import ZoneInfo

import pytest
from homeassistant.util import dt as dt_util

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
    legacy_item_key,
)
from custom_components.rehlko_energy.models import GeneratorData


@pytest.fixture
def tracker(monkeypatch) -> SeenTracker:
    class MemStore:
        def __init__(self, *a, **k) -> None:
            self.data = None
            self.saves = 0
            self.delay = None

        def async_delay_save(self, fn, delay) -> None:
            self.data = fn()
            self.saves += 1
            self.delay = delay

        async def async_save(self, data) -> None:
            self.data = data

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
    plain = {"deviceEventId": "OverCrank", "timestamp": "t"}
    assert item_key(plain).startswith(f"{legacy_item_key(plain)}|")
    assert legacy_item_key(plain) == "OverCrank|t"
    assert item_key({**plain, "id": ""}) == item_key(plain)  # an empty id is no id


def test_items_without_an_id_are_told_apart() -> None:
    low_battery = {"type": "Alert", "timestamp": "t", "message": "Low battery"}
    low_fuel = {**low_battery, "message": "Low fuel"}
    assert item_key(low_battery) != item_key(low_fuel)
    # Not by a field that can change after the fact: the item would come back as new.
    assert item_key({**low_battery, "isRead": True}) == item_key(low_battery)


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


def test_a_longer_window_is_remembered_not_announced(tracker: SeenTracker) -> None:
    from datetime import UTC, datetime, timedelta

    newest = datetime(2026, 11, 1, tzinfo=UTC)
    page = [
        {"id": 100 - i, "timestamp": (newest - timedelta(hours=i)).isoformat()} for i in range(50)
    ]
    # The first sight seeds.
    assert tracker.fresh(1, "notifications", page[:10], window=10) == []
    # A larger limit shows forty older notifications: history, not news.
    assert tracker.fresh(1, "notifications", page, window=50) == []
    later = {"id": 101, "timestamp": (newest + timedelta(hours=1)).isoformat()}
    assert tracker.fresh(1, "notifications", [later, *page], window=50) == [later]
    # One that reaches the service late, inside what was already shown, is still news.
    late = {"id": 102, "timestamp": (newest - timedelta(hours=5, minutes=30)).isoformat()}
    assert tracker.fresh(1, "notifications", [later, *page, late], window=50) == [late]
    # With the limit as it was, so is one dated before everything else.
    early = {"id": 103, "timestamp": (newest - timedelta(days=30)).isoformat()}
    assert tracker.fresh(1, "notifications", [later, *page, early], window=50) == [early]


BASE = datetime(2026, 1, 1, tzinfo=UTC)


def at(ident: Any, hours: float) -> dict[str, Any]:
    return {"id": ident, "timestamp": (BASE + timedelta(hours=hours)).isoformat()}


@pytest.fixture
def site_tz() -> Iterator[Callable[[str], None]]:
    before = dt_util.get_default_time_zone()
    yield lambda name: dt_util.set_default_time_zone(ZoneInfo(name))
    dt_util.set_default_time_zone(before)


def test_new_items_are_news_whatever_their_time_says(tracker: SeenTracker) -> None:
    tracker.fresh(1, "events", [at(1, 0), at(2, 1)])
    undated = {"id": 3}
    unreadable = {"id": 4, "timestamp": "yesterday"}
    clock_reset = {"id": 5, "timestamp": "2000-01-01T00:05:00"}  # a controller after power loss
    page = [undated, unreadable, clock_reset, at(1, 0), at(2, 1)]
    assert {item["id"] for item in tracker.fresh(1, "events", page)} == {3, 4, 5}
    assert tracker.fresh(1, "events", page) == []


def test_times_without_an_offset_are_the_sites(tracker: SeenTracker, site_tz) -> None:
    site_tz("America/New_York")
    seen = {"id": 1, "timestamp": "2026-11-16T14:30:00Z"}  # 09:30 in New York
    newer = {"id": 2, "timestamp": "2026-11-16T10:00:00"}  # 10:00 in New York, not UTC
    assert coord._sort_key(newer) > coord._sort_key(seen)
    tracker.fresh(1, "notifications", [seen], window=10)
    # A larger limit makes older items history: this one is not older.
    assert tracker.fresh(1, "notifications", [newer, seen], window=50) == [newer]


def test_an_item_listed_twice_is_announced_once(tracker: SeenTracker) -> None:
    tracker.fresh(1, "events", [at(1, 0)])
    assert tracker.fresh(1, "events", [at(2, 1), at(2, 1), at(1, 0)]) == [at(2, 1)]
    tracker.active_diff(1, "alerts", [])
    assert tracker.active_diff(1, "alerts", [at(7, 0), at(7, 0)]) == ([at(7, 0)], [])


def test_items_without_an_id_at_the_same_time_are_each_announced(tracker: SeenTracker) -> None:
    old = {"type": "Alert", "timestamp": "2026-11-16T09:00:00Z", "message": "Exercised"}
    tracker.fresh(1, "notifications", [old])
    low_battery = {"type": "Alert", "timestamp": "2026-11-16T12:00:00Z", "message": "Low battery"}
    low_fuel = {**low_battery, "message": "Low fuel"}
    assert tracker.fresh(1, "notifications", [low_battery, old]) == [low_battery]
    assert tracker.fresh(1, "notifications", [low_fuel, low_battery, old]) == [low_fuel]


def test_an_empty_first_answer_does_not_make_history_news(tracker: SeenTracker) -> None:
    assert tracker.fresh(1, "events", []) == []
    assert tracker.fresh(1, "events", []) == []
    # A new generator's backlog, or the empty answer was a fault: dated before the first read.
    backlog = [at(i, -i) for i in range(1, 40)]
    assert tracker.fresh(1, "events", backlog) == []
    later = {"id": 99, "timestamp": (dt_util.utcnow() + timedelta(minutes=1)).isoformat()}
    assert tracker.fresh(1, "events", [later, *backlog]) == [later]
    # An account's very first notification is news.
    assert tracker.fresh(2, "notifications", [], window=50) == []
    first = {"id": 1, "timestamp": (dt_util.utcnow() + timedelta(seconds=1)).isoformat()}
    assert tracker.fresh(2, "notifications", [first], window=50) == [first]


def test_ties_at_the_cut_keep_the_same_items(tracker: SeenTracker) -> None:
    noon = [at(i, 12) for i in range(coord.MAX_SEEN - 10)]
    eleven = [at(f"b{i}", 11) for i in range(20)]  # ten of these make the cut
    assert tracker.fresh(1, "events", noon + eleven) == []
    assert tracker.fresh(1, "events", noon + eleven[5:] + eleven[:5]) == []
    assert tracker.fresh(1, "events", noon + eleven[::-1]) == []


def test_an_item_that_comes_back_is_not_news(tracker: SeenTracker) -> None:
    first = [at(i, i) for i in range(coord.MAX_SEEN)]
    tracker.fresh(1, "events", first)
    newer = [at(i, i) for i in range(coord.MAX_SEEN, coord.MAX_SEEN + 50)]
    # The fifty oldest leave what is compared...
    assert len(tracker.fresh(1, "events", [*newer, *first])) == 50
    # ...and come back when the fifty newest are deleted.
    assert tracker.fresh(1, "events", first) == []


async def test_a_record_from_an_earlier_version_is_honoured(tracker: SeenTracker) -> None:
    # Newer than an item with an id: only its legacy key shows it was seen.
    old = {"deviceEventId": "OverCrank", "timestamp": at(0, 1)["timestamp"]}
    alert = {"deviceEventId": "LowFuel", "timestamp": at(0, 1)["timestamp"]}
    tracker._store.data = {
        "1": {"events": [legacy_item_key(old), "7"], "alerts": [legacy_item_key(alert)]},
        "2": {"events": []},
    }
    await tracker.async_load()
    # The first answer is read as the earlier version would: what is older than everything
    # seen may be history a larger window shows.
    history, news = at(6, -5), at(8, 2)
    page = [news, at(7, 0.5), old, history]
    assert tracker.fresh(1, "events", page) == [news]
    late = at(9, -10)
    assert tracker.fresh(1, "events", [*page, late]) == [late]
    assert tracker.active_diff(1, "alerts", [alert]) == ([], [])
    assert tracker.active_diff(1, "alerts", []) == ([], [item_key(alert)])
    # A feed that was empty: its first answer only seeds it.
    assert tracker.fresh(2, "events", [at(i, -i) for i in range(30)]) == []


@pytest.mark.parametrize(
    "stored",
    [
        ["not", "a", "mapping"],
        {"1": ["not", "a", "mapping"]},
        {"1": {"events": {"not": "a list"}}},
        {"1": {"events": None}},
        {"1": {"events": [1, 2]}},
        {"1": {"events": ["1"], "meta": "nonsense"}},
        {"1": {"events": ["1"], "meta": {"events": {"window": "ten"}}}},
        {"1": {"events": ["1"], "meta": {"events": {"since": "today"}}}},
    ],
)
async def test_a_damaged_record_starts_over(tracker: SeenTracker, stored, caplog) -> None:
    tracker._store.data = stored
    await tracker.async_load()
    assert "could not be read" in caplog.text
    page = [at(2, 1), at(1, 0)]
    tracker.fresh(1, "events", page)
    tracker.active_diff(1, "alerts", [])
    assert tracker.fresh(1, "events", [at(3, 2), *page]) == [at(3, 2)]


async def test_a_record_reloads_as_it_was_saved(tracker: SeenTracker, caplog) -> None:
    tracker.fresh(1, "events", [at(1, 0)])
    tracker.fresh(1, "notifications", [], window=50)
    tracker.active_diff(1, "alerts", [at(5, 0)])
    stored = json.loads(json.dumps(tracker._store.data))
    tracker._store.data = stored
    await tracker.async_load()
    assert tracker._data == stored
    assert "could not be read" not in caplog.text


def test_the_record_is_written_soon_and_only_on_change(tracker: SeenTracker) -> None:
    page = [at(1, 0)]
    tracker.fresh(1, "events", page)
    tracker.active_diff(1, "alerts", [])
    saves = tracker._store.saves
    tracker.fresh(1, "events", page)
    tracker.active_diff(1, "alerts", [])
    assert tracker._store.saves == saves
    tracker.fresh(1, "events", [at(2, 1), *page])
    assert tracker._store.saves == saves + 1
    assert tracker._store.delay <= 1


def test_a_departed_generator_is_forgotten(tracker: SeenTracker) -> None:
    tracker.fresh(1, "events", [at(1, 0)])
    tracker.fresh(2, "events", [at(1, 0)])
    assert tracker.device_ids() == {1, 2}
    tracker.forget(2)
    tracker.forget(3)
    assert tracker.device_ids() == {1}


def test_each_time_is_read_once(tracker: SeenTracker) -> None:
    page = [at(i, i) for i in range(100)]
    coord._parsed.cache_clear()
    with patch.object(coord, "parse_timestamp", wraps=coord.parse_timestamp) as parse:
        tracker.fresh(1, "events", page)
        sorted(page, key=coord._sort_key)  # as the coordinator orders a feed it fetched
        tracker.fresh(1, "events", [at(100, 100), *page])
    assert parse.call_count == 101


def test_an_id_is_the_same_however_it_is_written(tracker: SeenTracker) -> None:
    tracker.fresh(1, "events", [at(7, 0)])
    assert tracker.fresh(1, "events", [at(7.0, 0)]) == []
    assert tracker.fresh(1, "events", [at("7", 0)]) == []


async def test_a_closed_record_records_nothing(tracker: SeenTracker) -> None:
    tracker.fresh(1, "events", [at(1, 0)])
    tracker.active_diff(1, "alerts", [])
    await tracker.async_close()  # at unload
    saves = tracker._store.saves
    assert tracker.fresh(1, "events", [at(2, 1), at(1, 0)]) == []
    assert tracker.active_diff(1, "alerts", [at(5, 0)]) == ([], [])
    tracker.forget(1)
    assert tracker._store.saves == saves
    assert "2" not in tracker._data["1"]["events"]
