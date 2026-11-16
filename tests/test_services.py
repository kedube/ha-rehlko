"""The domain's actions, called through Home Assistant as an automation or the panel would."""

from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.core import Context
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError, Unauthorized
from homeassistant.helpers import device_registry as dr
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.rehlko_energy.const import DOMAIN

from .conftest import standby


@pytest.fixture
async def entry(hass, client, enable_custom_integrations):
    config_entry = MockConfigEntry(domain=DOMAIN, title="Test account", unique_id="owner", data={})
    config_entry.add_to_hass(hass)
    with patch("custom_components.rehlko_energy.build_client", return_value=client):
        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()
    yield config_entry
    # Writes schedule follow-up reads; unloading cancels them.
    await hass.config_entries.async_unload(config_entry.entry_id)


def device(hass, entry, identifier: str) -> str:
    for found in dr.async_entries_for_config_entry(dr.async_get(hass), entry.entry_id):
        if (DOMAIN, identifier) in found.identifiers:
            return found.id
    raise AssertionError(f"no device {identifier}")


async def call(hass, action: str, data: dict, **kwargs):
    return await hass.services.async_call(DOMAIN, action, data, blocking=True, **kwargs)


async def test_actions_are_for_administrators(hass, entry, hass_read_only_user):
    with pytest.raises(Unauthorized):
        await call(
            hass,
            "get_generator_data",
            {"device_id": device(hass, entry, "1")},
            return_response=True,
            context=Context(user_id=hass_read_only_user.id),
        )


async def test_the_transfer_switch_stands_for_its_generator(hass, entry):
    data = await call(
        hass,
        "get_generator_data",
        {"device_id": device(hass, entry, "1:ats")},
        return_response=True,
    )
    assert data["device"]["id"] == 1
    assert "devices" not in data["home"]


async def test_devices_that_are_not_generators_are_refused(hass, entry):
    with pytest.raises(ServiceValidationError) as err:
        await call(hass, "get_alerts", {"device_id": "no-such-device"}, return_response=True)
    assert err.value.translation_key == "device_not_found"
    account = device(hass, entry, f"account:{entry.entry_id}")
    with pytest.raises(ServiceValidationError) as err:
        await call(hass, "get_alerts", {"device_id": account}, return_response=True)
    assert err.value.translation_key == "not_a_generator"


async def test_reads_return_the_feeds(hass, entry, client):
    client.get_events.return_value = [
        {"id": i, "deviceEventId": "ExerciseStarted", "timestamp": f"2026-11-{10 + i}T10:00:00Z"}
        for i in range(5)
    ]
    client.get_maintenance_notes.return_value = [{"id": 1, "contents": "Oil changed"}]
    await entry.runtime_data.async_refresh_everything()
    generator = device(hass, entry, "1")
    log = await call(
        hass, "get_activity_log", {"device_id": generator, "limit": 2}, return_response=True
    )
    assert [event["id"] for event in log["events"]] == [4, 3]
    assert log["events"][0]["name"] == "Exercise started"
    history = await call(
        hass, "get_maintenance_history", {"device_id": generator}, return_response=True
    )
    assert history["notes"][0]["contents"] == "Oil changed"
    assert history["maintenance_period_days"] == 365
    assert await call(hass, "get_alerts", {"device_id": generator}, return_response=True) == {
        "alerts": []
    }
    assert await call(
        hass, "get_notifications", {"device_id": generator}, return_response=True
    ) == {"notifications": []}


async def test_parameter_definitions_use_the_controllers_serial(hass, entry, client):
    client.get_parameter_definitions = AsyncMock(return_value=[{"id": 7}])
    generator = device(hass, entry, "1")
    data = await call(
        hass, "get_parameter_definitions", {"device_id": generator}, return_response=True
    )
    assert data == {"definitions": [{"id": 7}]}
    client.get_parameter_definitions.assert_awaited_once_with(1, "generators", "GEN1")
    await call(
        hass,
        "get_parameter_definitions",
        {"device_id": generator, "kind": "ats"},
        return_response=True,
    )
    client.get_parameter_definitions.assert_awaited_with(1, "ats", "ATS1")


async def test_a_running_generator_is_not_started_again(hass, entry, client):
    client.start_exercise = AsyncMock()
    with pytest.raises(HomeAssistantError) as err:
        await call(hass, "start_exercise", {"device_id": device(hass, entry, "1")})
    assert err.value.translation_key == "not_ready"
    client.start_exercise.assert_not_awaited()


async def test_a_read_only_setting_is_refused_before_the_cloud_is_asked(hass, entry, client):
    client.get_device.return_value["pim"]["parameters"][0]["isReadOnly"] = True
    await entry.runtime_data.async_refresh()
    client.set_peripheral_value = AsyncMock()
    with pytest.raises(HomeAssistantError) as err:
        await call(
            hass,
            "set_peripheral_value",
            {"device_id": device(hass, entry, "1"), "definition_id": "2", "value": False},
        )
    assert err.value.translation_key == "read_only"
    client.set_peripheral_value.assert_not_awaited()


async def test_writes_reach_the_cloud_as_the_app_sends_them(hass, entry, client):
    standby(client)
    await entry.runtime_data.async_refresh()
    for name in (
        "start_exercise",
        "set_exercise_schedule",
        "add_maintenance_note",
        "set_controller_clock",
        "rename_peripheral",
        "set_peripheral_value",
    ):
        setattr(client, name, AsyncMock(return_value=None))
    generator = device(hass, entry, "1")

    await call(hass, "start_exercise", {"device_id": generator, "mode": "unloaded_full_speed"})
    client.start_exercise.assert_awaited_once_with(1, "UnloadedFullSpeed")

    await call(
        hass,
        "set_exercise_schedule",
        {"device_id": generator, "frequency": "weekly", "duration": 30},
    )
    client.set_exercise_schedule.assert_awaited_once_with(
        1,
        frequency="Weekly",
        mode="Unloaded",
        duration_minutes=30,
        next_start="2026-11-22T14:00:00",  # unchanged, in the controller's own form
    )

    await call(hass, "add_maintenance_note", {"device_id": generator, "note": " Oil changed "})
    client.add_maintenance_note.assert_awaited_once_with(1, "Oil changed")

    await call(
        hass,
        "sync_controller_clock",
        {"device_id": generator, "timestamp": "2026-11-16T09:30:00"},
    )
    # The controller keeps local wall-clock time without an offset, as the service reports it.
    client.set_controller_clock.assert_awaited_once_with(1, "2026-11-16T09:30:00")

    await call(
        hass,
        "rename_peripheral",
        {"device_id": generator, "definition_id": "1", "name": "Pool pump"},
    )
    client.rename_peripheral.assert_awaited_once_with(1, "1", "Pool pump")

    await call(
        hass,
        "set_peripheral_value",
        {"device_id": generator, "definition_id": "1", "value": "Off"},
    )
    client.set_peripheral_value.assert_awaited_once_with(1, "1", "Off")


async def test_refresh_reads_everything_again(hass, entry, client):
    client.get_me.reset_mock()
    client.get_events.reset_mock()
    await call(hass, "refresh", {})
    client.get_me.assert_awaited_once()
    client.get_events.assert_awaited_once()
