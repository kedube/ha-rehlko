"""Control platforms: buttons, selects, numbers, switches, text, events, calendar, update.

Each entity is constructed against the sample generator and its action is driven through a
fake coordinator that records the call — verifying availability gates, option mapping, value
extraction and that writes reach the right coordinator method.
"""

from __future__ import annotations

from datetime import datetime

import pytest

from custom_components.rehlko_energy import button as button_mod
from custom_components.rehlko_energy import calendar as calendar_mod
from custom_components.rehlko_energy import event as event_mod
from custom_components.rehlko_energy import number as number_mod
from custom_components.rehlko_energy import select as select_mod
from custom_components.rehlko_energy import switch as switch_mod
from custom_components.rehlko_energy import text as text_mod
from custom_components.rehlko_energy import update as update_mod
from custom_components.rehlko_energy.coordinator import FEED_POWER, FeedItem
from custom_components.rehlko_energy.models import GeneratorData

from .test_entities import FakeCoordinator, build_sample_gen


@pytest.fixture
def sample_gen() -> GeneratorData:
    return build_sample_gen()


class RecordingCoordinator(FakeCoordinator):
    def __init__(self, gen: GeneratorData, notification_settings=None) -> None:
        super().__init__(gen)
        self.data.notification_settings = notification_settings
        self.calls: list[tuple[str, tuple, dict]] = []
        self._feed_cbs: list = []

    def __getattr__(self, name: str):
        if name.startswith("async_"):

            async def recorder(*args, **kwargs):
                self.calls.append((name, args, kwargs))

            return recorder
        raise AttributeError(name)

    def async_add_feed_listener(self, cb):
        self._feed_cbs.append(cb)
        return lambda: None


async def test_buttons_build_and_dispatch(sample_gen) -> None:
    coord = RecordingCoordinator(sample_gen)
    for desc in button_mod.BUTTONS:
        entity = button_mod.RehlkoButton(coord, 1, desc)
        assert entity.available
        await entity.async_press()
    names = [c[0] for c in coord.calls]
    assert "async_start_exercise" in names
    assert "async_stop_exercise" in names
    assert "async_sync_controller_clock" in names


def test_start_button_availability_gates(sample_gen) -> None:
    coord = RecordingCoordinator(sample_gen)
    start = next(d for d in button_mod.BUTTONS if d.key == "start_exercise")
    # Available when online and the controller supports scheduling (readiness is enforced at
    # press time by the coordinator, which raises a clear error otherwise).
    assert button_mod.RehlkoButton(coord, 1, start).available
    # Offline -> unavailable.
    sample_gen.device["isConnected"] = False
    assert not button_mod.RehlkoButton(coord, 1, start).available
    # A controller that cannot schedule remotely -> unavailable.
    sample_gen.device["isConnected"] = True
    sample_gen.device["product"] = "Apm402"
    assert not button_mod.RehlkoButton(coord, 1, start).available


async def test_select_maps_option_to_wire_value(sample_gen) -> None:
    coord = RecordingCoordinator(sample_gen)
    desc = next(d for d in select_mod.SELECTS if d.key == "exercise_mode")
    entity = select_mod.ExerciseSelect(coord, 1, desc)
    assert entity.current_option == "unloaded"
    assert "loaded_full_speed" in entity.options
    await entity.async_select_option("loaded_full_speed")
    assert coord.calls[-1] == ("async_set_exercise_schedule", (1,), {"mode": "LoadedFullSpeed"})


async def test_exercise_duration_number(sample_gen) -> None:
    coord = RecordingCoordinator(sample_gen)
    entity = number_mod.ExerciseDurationNumber(coord, 1)
    assert entity.native_value == 20.0
    await entity.async_set_native_value(30)
    assert coord.calls[-1] == ("async_set_exercise_schedule", (1,), {"duration_minutes": 30})


async def test_peripheral_number_writes_value(sample_gen) -> None:
    # Make the loadShed parameter numeric so a PeripheralNumber is appropriate.
    sample_gen.details["loadShed"]["parameters"][0]["value"] = 5
    coord = RecordingCoordinator(sample_gen)
    entity = number_mod.PeripheralNumber(coord, 1, "loadShed", 1)
    assert entity.native_value == 5.0
    await entity.async_set_native_value(7)
    assert coord.calls[-1][0] == "async_set_peripheral_value"
    assert coord.calls[-1][1] == (1, 1, 7)


async def test_notification_switch(sample_gen) -> None:
    coord = RecordingCoordinator(sample_gen, notification_settings={"sendShutdowns": True})
    entity = switch_mod.NotificationSettingSwitch(coord, "sendShutdowns")
    assert entity.is_on is True
    await entity.async_turn_off()
    assert coord.calls[-1] == ("async_set_notification_setting", ("sendShutdowns", False), {})


async def test_auto_firmware_switch(sample_gen) -> None:
    coord = RecordingCoordinator(sample_gen)
    entity = switch_mod.AutoFirmwareUpdateSwitch(coord, 1)
    assert entity.is_on is True
    await entity.async_turn_off()
    assert coord.calls[-1] == ("async_update_device", (1,), {"autoFirmwareUpdateEnabled": False})


async def test_peripheral_switch(sample_gen) -> None:
    coord = RecordingCoordinator(sample_gen)
    entity = switch_mod.PeripheralSwitch(coord, 1, "pim", 2)
    assert entity.is_on is True
    await entity.async_turn_off()
    assert coord.calls[-1] == ("async_set_peripheral_value", (1, 2, False), {})


async def test_generator_name_text(sample_gen) -> None:
    coord = RecordingCoordinator(sample_gen)
    entity = text_mod.GeneratorNameText(coord, 1)
    assert entity.native_value == "Home Generator"
    await entity.async_set_value("  New Name  ")
    assert coord.calls[-1] == ("async_update_device", (1,), {"displayName": "New Name"})


def test_update_entity_versions(sample_gen) -> None:
    coord = RecordingCoordinator(sample_gen)
    entity = update_mod.FirmwareUpdate(coord, 1)
    assert entity.installed_version == "3.14"
    assert entity.latest_version == "3.15"
    assert "3.15" not in (entity.release_summary or "") or "Released" in (
        entity.release_summary or ""
    )


def test_update_summary_is_translatable(sample_gen) -> None:
    coord = RecordingCoordinator(sample_gen)
    entity = update_mod.FirmwareUpdate(coord, 1)
    sample_gen.details["autoFirmwareUpdateEnabled"] = False
    english = entity.release_summary
    assert english.startswith("Released: 2026-11-01. Scheduled installation: 2026-")
    assert english.endswith("Automatic firmware updates are off for this generator.")
    prefix = "update.firmware.state_attributes.release_summary.state"
    # One label translated, the other missing: the English label stands in for it.
    entity._texts = {f"{prefix}.released": "Publicado"}
    summary = entity.release_summary
    assert summary.startswith("Publicado: 2026-11-01. Scheduled installation: 2026-")
    assert len(summary) <= 255


async def test_blank_names_are_rejected(sample_gen) -> None:
    from homeassistant.exceptions import ServiceValidationError

    coord = RecordingCoordinator(sample_gen)
    entity = text_mod.GeneratorNameText(coord, 1)
    with pytest.raises(ServiceValidationError) as raised:
        await entity.async_set_value("   ")
    assert raised.value.translation_key == "empty_name"
    assert not coord.calls


def test_event_entity_fires_on_feed(sample_gen) -> None:
    coord = RecordingCoordinator(sample_gen)
    desc = next(d for d in event_mod.EVENTS if d.key == "power")
    entity = event_mod.RehlkoEvent(coord, 1, desc)
    fired: list[tuple[str, dict]] = []
    entity._trigger_event = lambda t, a: fired.append((t, a))  # type: ignore[method-assign]
    entity.async_write_ha_state = lambda: None  # type: ignore[method-assign]
    item = FeedItem(FEED_POWER, sample_gen, {"power_source": "Generator"}, "generator_started")
    entity._on_feed(item)
    assert fired and fired[0][0] == "generator_started"
    # An event for a different generator is ignored.
    other = GeneratorData(device_id=2, home={}, device={}, details={})
    entity._on_feed(FeedItem(FEED_POWER, other, {}, "generator_stopped"))
    assert len(fired) == 1


def test_calendar_projects_schedule(sample_gen) -> None:
    start = datetime.fromisoformat("2026-11-01T00:00:00+00:00")
    end = datetime.fromisoformat("2026-12-31T00:00:00+00:00")
    projected = calendar_mod.exercise_events(sample_gen, start, end)
    summaries = [e.summary for e in projected]
    assert any("Exercise" in s for s in summaries)
    assert "Maintenance due" not in summaries  # due date is in 2027
    # Weekly schedule projects multiple occurrences within the window.
    sample_gen.details["exercise"]["frequency"] = "Weekly"
    weekly = calendar_mod.exercise_events(sample_gen, start, end)
    assert sum(1 for e in weekly if e.summary.startswith("Exercise")) >= 4


def test_calendar_titles_use_home_assistants_language(sample_gen) -> None:
    start = datetime.fromisoformat("2026-11-01T00:00:00+00:00")
    end = datetime.fromisoformat("2027-06-01T00:00:00+00:00")
    texts = {
        "calendar.schedule.state_attributes.message.state.exercise": "Ejercicio",
        "calendar.schedule.state_attributes.message.state.last_exercise": "Último ejercicio",
        "calendar.schedule.state_attributes.message.state.maintenance_due": "Mantenimiento",
        "calendar.schedule.state_attributes.description.state.scheduled": "Próximo ejercicio.",
        "select.exercise_mode.state.unloaded": "Sin carga",
    }
    events = calendar_mod.exercise_events(sample_gen, start, end, texts)
    summaries = [event.summary for event in events]
    assert "Último ejercicio" in summaries
    assert "Ejercicio (Sin carga)" in summaries
    assert "Mantenimiento" in summaries
    first = next(event for event in events if event.summary == "Ejercicio (Sin carga)")
    assert first.description == "Próximo ejercicio."
    # Text without a translation keeps its English.
    projected = [event for event in events if event.summary == "Ejercicio (Sin carga)"][1]
    assert projected.description == "Projected from the exercise schedule."
    assert len({event.uid for event in events}) == len(events)


def test_calendar_next_event_skips_the_last_run_in_any_language(sample_gen, monkeypatch) -> None:
    now = datetime.fromisoformat("2026-11-08T14:10:00+00:00")  # during the last exercise
    monkeypatch.setattr(calendar_mod.dt_util, "now", lambda: now)
    entity = calendar_mod.ExerciseCalendar(RecordingCoordinator(sample_gen), 1)
    entity._texts = {
        "calendar.schedule.state_attributes.message.state.last_exercise": "Último ejercicio",
        "calendar.schedule.state_attributes.message.state.exercise": "Ejercicio",
    }
    upcoming = entity.event
    assert upcoming is not None
    assert upcoming.summary.startswith("Ejercicio")
    assert upcoming.start > now


@pytest.mark.parametrize(
    "platform",
    [button_mod, select_mod, number_mod, switch_mod, text_mod, event_mod, calendar_mod, update_mod],
)
def test_platforms_expose_setup(platform) -> None:
    assert hasattr(platform, "async_setup_entry")


def test_monthly_calendar_keeps_original_day_after_short_month(sample_gen) -> None:
    sample_gen.details["exercise"].update(
        frequency="Monthly", nextStartTimestamp="2027-01-31T14:00:00Z"
    )
    projected = calendar_mod.exercise_events(
        sample_gen,
        datetime.fromisoformat("2027-01-01T00:00:00+00:00"),
        datetime.fromisoformat("2027-04-01T00:00:00+00:00"),
    )
    days = [event.start.day for event in projected if event.summary.startswith("Exercise")]
    assert days == [31, 28, 31]


def test_weekly_calendar_preserves_local_time_across_dst(sample_gen, monkeypatch) -> None:
    from zoneinfo import ZoneInfo

    timezone = ZoneInfo("America/New_York")
    monkeypatch.setattr(calendar_mod.dt_util, "get_default_time_zone", lambda: timezone)
    sample_gen.details["exercise"].update(
        frequency="Weekly", nextStartTimestamp="2027-03-07T19:00:00Z"
    )
    projected = calendar_mod.exercise_events(
        sample_gen,
        datetime.fromisoformat("2027-03-01T00:00:00+00:00"),
        datetime.fromisoformat("2027-03-22T00:00:00+00:00"),
    )
    starts = [event.start for event in projected if event.summary.startswith("Exercise")]
    assert len(starts) == 3
    assert [when.astimezone(timezone).hour for when in starts] == [14, 14, 14]
    assert starts[0].utcoffset() != starts[-1].utcoffset()
