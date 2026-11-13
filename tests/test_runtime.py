"""Exercise the integration lifecycle against Home Assistant, without the cloud."""

import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.exceptions import ConfigEntryNotReady, HomeAssistantError
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.rehlko_energy import async_setup_entry
from custom_components.rehlko_energy.api import RehlkoConnectionError
from custom_components.rehlko_energy.const import DOMAIN
from custom_components.rehlko_energy.coordinator import RehlkoCoordinator
from custom_components.rehlko_energy.models import AccountData
from custom_components.rehlko_energy.sidebar import STATIC_URL, URL_PATH, async_setup_sidebar

from .test_entities import SAMPLE_DEVICE, build_sample_gen


@pytest.fixture
def entry(hass):
    config_entry = MockConfigEntry(domain=DOMAIN, title="Test account", unique_id="owner", data={})
    config_entry.add_to_hass(hass)
    return config_entry


async def test_setup_reload_unload(hass, entry, client, enable_custom_integrations, hass_ws_client):
    with patch("custom_components.rehlko_energy.build_client", return_value=client):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        assert entry.state is ConfigEntryState.LOADED
        assert hass.states.get("sensor.home_generator_battery_voltage").state == "13.6"
        assert hass.states.get("button.home_generator_start_exercise") is not None
        assert URL_PATH in hass.data["frontend_panels"]
        assert hass.data["frontend_panels"][URL_PATH].require_admin
        ws = await hass_ws_client(hass)
        await ws.send_json({"id": 1, "type": f"{DOMAIN}/subscribe"})
        assert (await ws.receive_json())["success"]
        snapshot = (await ws.receive_json())["event"]
        assert snapshot["generators"][0]["device_id"] == 1
        assert snapshot["generators"][0]["available"]
        assert snapshot["generators"][0]["entities"]["sensor.battery_voltage"]
        # The panel gets the controller's address as an address; the payload stays as sent.
        assert snapshot["generators"][0]["derived"]["ip_address"] == "10.0.0.5"
        assert (
            snapshot["generators"][0]["device"]["deviceIpAddress"]
            == SAMPLE_DEVICE["deviceIpAddress"]
        )
        # The firmware entity shows its icon, not the integration's logo.
        firmware = hass.states.get("update.home_generator_controller_firmware")
        assert firmware is not None and "entity_picture" not in firmware.attributes
        await ws.close()
        assert await hass.config_entries.async_reload(entry.entry_id)
        await hass.async_block_till_done()
        assert entry.state is ConfigEntryState.LOADED
        assert await hass.config_entries.async_unload(entry.entry_id)
        assert entry.state is ConfigEntryState.NOT_LOADED


async def test_setup_connection_failure_retries(hass, entry, client):
    entry._async_set_state(hass, ConfigEntryState.SETUP_IN_PROGRESS, None)
    client.get_homes.side_effect = RehlkoConnectionError("offline")
    with (
        patch("custom_components.rehlko_energy.build_client", return_value=client),
        pytest.raises(ConfigEntryNotReady),
    ):
        await async_setup_entry(hass, entry)


async def test_stale_generator_disables_entities_and_writes(hass, entry, client):
    coordinator = RehlkoCoordinator(hass, entry, client)
    old = build_sample_gen()
    coordinator.async_set_updated_data(AccountData(generators={1: old}))
    client.get_device.side_effect = RehlkoConnectionError("offline")
    data = await coordinator._async_update_data()
    stale = data.generators[1]
    assert stale.details == old.details
    assert not stale.details_available
    coordinator.data = data
    with pytest.raises(HomeAssistantError):
        await coordinator.async_start_exercise(1)
    client.start_exercise.assert_not_called()


async def test_notification_writes_preserve_concurrent_changes(hass, entry, client):
    import asyncio

    coordinator = RehlkoCoordinator(hass, entry, client)
    coordinator.data = AccountData(
        notification_settings={"sendShutdowns": True, "sendWarnings": True}
    )
    writes = []

    async def write(settings):
        await asyncio.sleep(0)
        writes.append(dict(settings))

    client.set_notification_settings = AsyncMock(side_effect=write)
    with patch.object(coordinator, "async_request_refresh", new_callable=AsyncMock):
        await asyncio.gather(
            coordinator.async_set_notification_setting("sendShutdowns", False),
            coordinator.async_set_notification_setting("sendWarnings", False),
        )
    assert writes[-1] == {"sendShutdowns": False, "sendWarnings": False}


async def test_bundle_is_served_at_registered_url(hass, hass_client):
    assert await async_setup_component(hass, "panel_custom", {})
    await async_setup_sidebar(hass)
    # Repeated setup must not register duplicate aiohttp routes or commands.
    await async_setup_sidebar(hass)
    http = await hass_client()
    response = await http.get(STATIC_URL + "?v=test")
    assert response.status == 200
    assert "javascript" in response.content_type
    assert "rehlko-energy-panel" in await response.text()


async def test_failed_initial_feeds_do_not_announce_historical_items(hass, entry, client):
    coordinator = RehlkoCoordinator(hass, entry, client)
    client.get_events.side_effect = RehlkoConnectionError("temporary failure")
    with patch.object(coordinator, "_fire") as fire:
        coordinator.data = await coordinator._async_update_data()
        client.get_events.side_effect = None
        client.get_events.return_value = [{"id": 1, "timestamp": "2026-01-01T00:00:00Z"}]
        coordinator.data = await coordinator._async_update_data()
        fire.assert_not_called()
        client.get_events.return_value.insert(0, {"id": 2, "timestamp": "2026-01-02T00:00:00Z"})
        coordinator._force_feeds.add(1)
        coordinator.data = await coordinator._async_update_data()
        fire.assert_called_once()
        assert fire.call_args.args[0].item["id"] == 2


# How long the machine has been up, in seconds: the monotonic clock counts from boot. The first
# three are a host that has just started, which is when Home Assistant itself usually starts.
UPTIMES = [5.0, 45.0, 119.0, 5000.0]
MONOTONIC = "custom_components.rehlko_energy.coordinator.time.monotonic"


@pytest.mark.parametrize("uptime", UPTIMES)
async def test_new_generator_fetches_feeds_before_next_global_interval(hass, entry, client, uptime):
    with patch(MONOTONIC, return_value=uptime):
        coordinator = RehlkoCoordinator(hass, entry, client)
        coordinator.data = await coordinator._async_update_data()
        client.get_events.reset_mock()
        client.get_homes.return_value[0]["devices"].append({**SAMPLE_DEVICE, "id": 2})
        coordinator.data = await coordinator._async_update_data()
    client.get_events.assert_awaited_once_with(2, SAMPLE_DEVICE["deviceHost"])


@pytest.mark.parametrize("uptime", UPTIMES)
async def test_the_first_refresh_reads_everything_however_recently_the_host_booted(
    hass, entry, client, uptime
):
    with patch(MONOTONIC, return_value=uptime):
        coordinator = RehlkoCoordinator(hass, entry, client)
        coordinator.data = await coordinator._async_update_data()
        # The account and its notification settings, not only the generators.
        assert coordinator.data.me == {"id": "owner"}
        assert coordinator.data.notification_settings == {
            "sendShutdowns": True,
            "sendWarnings": True,
        }
        client.get_events.assert_awaited_once()
        # A second refresh at the same moment has nothing due.
        for call in (client.get_me, client.get_notification_settings, client.get_events):
            call.reset_mock()
        coordinator.data = await coordinator._async_update_data()
    for call in (client.get_me, client.get_notification_settings, client.get_events):
        call.assert_not_awaited()


async def test_feeds_and_account_are_read_again_once_their_intervals_pass(hass, entry, client):
    with patch(MONOTONIC, return_value=10.0) as clock:
        coordinator = RehlkoCoordinator(hass, entry, client)
        coordinator.data = await coordinator._async_update_data()
        client.get_events.reset_mock()
        client.get_me.reset_mock()
        clock.return_value = 10.0 + 121.0  # past the two-minute feed interval
        coordinator.data = await coordinator._async_update_data()
        client.get_events.assert_awaited_once()
        client.get_me.assert_not_awaited()
        clock.return_value = 10.0 + 901.0  # past the fifteen-minute account interval
        coordinator.data = await coordinator._async_update_data()
        client.get_me.assert_awaited_once()


async def test_new_generators_get_all_platform_entities(
    hass, entry, client, enable_custom_integrations
):
    with patch("custom_components.rehlko_energy.build_client", return_value=client):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        client.get_homes.return_value[0]["devices"].append(
            {**SAMPLE_DEVICE, "id": 2, "displayName": "Second generator", "serialNumber": "SN2"}
        )
        await entry.runtime_data.async_refresh()
        await hass.async_block_till_done()
        for entity_id in (
            "button.second_generator_start_exercise",
            "calendar.second_generator_exercise_and_maintenance",
            "select.second_generator_exercise_mode",
            "datetime.second_generator_next_exercise_start",
            "event.second_generator_power_event",
            "update.second_generator_controller_firmware",
        ):
            assert hass.states.get(entity_id) is not None, entity_id


async def test_unreachable_generator_is_logged_once_and_on_recovery(hass, entry, client, caplog):
    import logging

    coordinator = RehlkoCoordinator(hass, entry, client)
    coordinator.data = await coordinator._async_update_data()
    client.get_device.side_effect = RehlkoConnectionError("offline")
    caplog.set_level(logging.INFO, logger="custom_components.rehlko_energy")
    for _ in range(3):
        coordinator.data = await coordinator._async_update_data()
    assert caplog.text.count("Could not refresh Home Generator") == 1
    client.get_device.side_effect = None
    coordinator.data = await coordinator._async_update_data()
    assert caplog.text.count("Home Generator is reporting again") == 1
    assert coordinator.data.generators[1].details_available


async def test_service_outage_is_a_translated_update_failure(hass, entry, client):
    from homeassistant.helpers.update_coordinator import UpdateFailed

    coordinator = RehlkoCoordinator(hass, entry, client)
    client.get_homes.side_effect = RehlkoConnectionError("GET /homeowner/homes: timeout")
    with pytest.raises(UpdateFailed) as raised:
        await coordinator._async_update_data()
    assert raised.value.translation_key == "unavailable"
    assert "timeout" in str(raised.value)


async def test_expired_sign_in_starts_reauthentication(hass, entry, client):
    from homeassistant.exceptions import ConfigEntryAuthFailed

    from custom_components.rehlko_energy.api import RehlkoAuthError

    coordinator = RehlkoCoordinator(hass, entry, client)
    client.get_homes.side_effect = RehlkoAuthError("refresh token revoked", reason="invalid_grant")
    with pytest.raises(ConfigEntryAuthFailed) as raised:
        await coordinator._async_update_data()
    assert raised.value.translation_key == "auth_failed"


async def test_seen_items_are_saved_before_a_reload(
    hass, entry, client, hass_storage, enable_custom_integrations
):
    """A reload inside the save delay must not re-announce what was just announced."""
    from custom_components.rehlko_energy.const import STORAGE_KEY_SEEN

    client.get_events.return_value = [{"id": 1, "timestamp": "2026-01-01T00:00:00Z"}]
    with patch("custom_components.rehlko_energy.build_client", return_value=client):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        assert await hass.config_entries.async_unload(entry.entry_id)
    stored = hass_storage[f"{STORAGE_KEY_SEEN}.{entry.entry_id}"]["data"]
    assert stored["1"]["events"] == ["1"]


async def test_sidebar_title_uses_the_servers_language(hass):
    from custom_components.rehlko_energy.sidebar import TITLES

    hass.config.language = "fr"
    assert await async_setup_component(hass, "panel_custom", {})
    MockConfigEntry(domain=DOMAIN, title="Test", data={}).add_to_hass(hass)
    await async_setup_sidebar(hass)
    assert hass.data["frontend_panels"][URL_PATH].sidebar_title == TITLES["fr"]


async def test_calendar_and_update_load_texts_in_the_servers_language(
    hass, entry, client, enable_custom_integrations
):
    hass.config.language = "es"
    with patch("custom_components.rehlko_energy.build_client", return_value=client):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    spanish = json.loads(
        (
            Path(__file__).parent.parent / "custom_components/rehlko_energy/translations/es.json"
        ).read_text(encoding="utf-8")
    )
    calendar = spanish["entity"]["calendar"]["schedule"]
    summaries = calendar["state_attributes"]["message"]["state"]
    # Home Assistant derives entity IDs from names in its own language, so look by domain.
    (state,) = hass.states.async_all("calendar")
    assert state.name.endswith(calendar["name"])
    assert state.attributes["message"].startswith(summaries["exercise"])
    (update,) = hass.states.async_all("update")
    released = spanish["entity"]["update"]["firmware"]["state_attributes"]["release_summary"]
    assert update.attributes["release_summary"].startswith(
        f"{released['state']['released']}: 2026-11-01."
    )


async def test_old_unique_ids_migrate_and_entities_keep_their_ids(
    hass, entry, client, enable_custom_integrations
):
    """An install from before per-account IDs keeps its entities, names and history."""
    from homeassistant.helpers import entity_registry as er

    registry = er.async_get(hass)
    old = registry.async_get_or_create(
        "sensor", DOMAIN, "1-battery_voltage", config_entry=entry, suggested_object_id="my_battery"
    )
    account = registry.async_get_or_create(
        "switch", DOMAIN, f"account-{entry.entry_id}-notify-sendWarnings", config_entry=entry
    )
    assert entry.minor_version == 1
    with patch("custom_components.rehlko_energy.build_client", return_value=client):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    assert entry.minor_version == 2
    assert registry.async_get(old.entity_id).unique_id == f"{entry.entry_id}-1-battery_voltage"
    assert registry.async_get(account.entity_id).unique_id == account.unique_id
    # The platform adopted the migrated entry instead of creating a second battery sensor.
    assert hass.states.get("sensor.my_battery").state == "13.6"
    assert hass.states.get("sensor.home_generator_battery_voltage") is None


async def test_catch_all_entities_are_registered_but_not_recorded(
    hass, entry, client, enable_custom_integrations
):
    from homeassistant.helpers import entity_registry as er

    client.get_device.return_value["someNewReading"] = 42
    client.get_device.return_value["someNewFlag"] = True
    with patch("custom_components.rehlko_energy.build_client", return_value=client):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    registry = er.async_get(hass)
    for platform, key in (("sensor", "someNewReading"), ("binary_sensor", "someNewFlag")):
        entity_id = registry.async_get_entity_id(
            platform, DOMAIN, f"{entry.entry_id}-1-extra-{key}"
        )
        assert entity_id is not None, key
        assert registry.async_get(entity_id).disabled_by is er.RegistryEntryDisabler.INTEGRATION
        assert hass.states.get(entity_id) is None


async def test_generators_that_leave_the_account_lose_their_devices(
    hass, entry, client, enable_custom_integrations
):
    from homeassistant.helpers import device_registry as dr

    client.get_homes.return_value[0]["devices"].append(
        {**SAMPLE_DEVICE, "id": 2, "displayName": "Cabin generator", "serialNumber": "SN2"}
    )
    with patch("custom_components.rehlko_energy.build_client", return_value=client):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        registry = dr.async_get(hass)
        coordinator = entry.runtime_data

        def devices() -> set[str]:
            return {
                identifier
                for device in dr.async_entries_for_config_entry(registry, entry.entry_id)
                for _, identifier in device.identifiers
            }

        everything = devices()
        assert {"1", "1:ats", "2", "2:ats"} <= everything

        # One empty answer is treated as a fault of the service, however often it repeats.
        homes = client.get_homes.return_value
        client.get_homes.return_value = []
        for _ in range(5):
            await coordinator.async_refresh()
        assert devices() == everything

        # The cabin is sold. Its devices go only after it has been missing for three polls.
        client.get_homes.return_value = [{**homes[0], "devices": homes[0]["devices"][:1]}]
        await coordinator.async_refresh()
        await coordinator.async_refresh()
        assert {"2", "2:ats"} <= devices()
        await coordinator.async_refresh()
        await hass.async_block_till_done()
        assert devices() == everything - {"2", "2:ats"}
        assert hass.states.get("sensor.cabin_generator_battery_voltage") is None
        assert hass.states.get("sensor.home_generator_battery_voltage") is not None


async def test_the_transfer_switch_is_linked_to_its_generator(
    hass, entry, client, enable_custom_integrations
):
    from homeassistant.helpers import device_registry as dr

    with patch("custom_components.rehlko_energy.build_client", return_value=client):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    devices = {
        identifier: device
        for device in dr.async_entries_for_config_entry(dr.async_get(hass), entry.entry_id)
        for _, identifier in device.identifiers
    }
    assert devices["1:ats"].via_device_id == devices["1"].id
    assert devices["1"].via_device_id is None


async def test_a_generator_that_comes_back_is_not_removed(
    hass, entry, client, enable_custom_integrations
):
    from homeassistant.helpers import device_registry as dr

    both = [SAMPLE_DEVICE, {**SAMPLE_DEVICE, "id": 2, "displayName": "Cabin", "serialNumber": "S2"}]
    client.get_homes.return_value = [{"id": 1, "devices": both}]
    with patch("custom_components.rehlko_energy.build_client", return_value=client):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        coordinator = entry.runtime_data
        for present in (False, False, True, False, False, True):
            client.get_homes.return_value = [{"id": 1, "devices": both if present else both[:1]}]
            await coordinator.async_refresh()
    devices = dr.async_entries_for_config_entry(dr.async_get(hass), entry.entry_id)
    assert any((DOMAIN, "2") in device.identifiers for device in devices)


async def test_the_panel_is_sent_bulky_fields_only_when_they_change(
    hass, entry, client, enable_custom_integrations, hass_ws_client
):
    client.get_events.return_value = [{"id": 1, "timestamp": "2026-01-01T00:00:00Z"}]
    with patch("custom_components.rehlko_energy.build_client", return_value=client):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        ws = await hass_ws_client(hass)
        await ws.send_json({"id": 1, "type": f"{DOMAIN}/subscribe"})
        assert (await ws.receive_json())["success"]
        first = (await ws.receive_json())["event"]["generators"][0]
        assert first["events"] == [{"id": 1, "timestamp": "2026-01-01T00:00:00Z"}]
        assert first["entities"]["sensor.battery_voltage"]

        coordinator = entry.runtime_data
        await coordinator.async_refresh()
        unchanged = (await ws.receive_json())["event"]["generators"][0]
        for field in ("events", "notifications", "maintenance_notes", "entities"):
            assert field not in unchanged
        assert unchanged["details"]["batteryVoltageV"] == 13.6
        assert len(json.dumps(unchanged)) < len(json.dumps(first))

        client.get_events.return_value = [
            {"id": 2, "timestamp": "2026-01-02T00:00:00Z"},
            {"id": 1, "timestamp": "2026-01-01T00:00:00Z"},
        ]
        await coordinator.async_refresh_everything()
        changed = (await ws.receive_json())["event"]["generators"][0]
        assert [event["id"] for event in changed["events"]] == [2, 1]
        assert "notifications" not in changed

        # A second panel starts from a complete snapshot of its own.
        other = await hass_ws_client(hass)
        await other.send_json({"id": 1, "type": f"{DOMAIN}/subscribe"})
        assert (await other.receive_json())["success"]
        assert "events" in (await other.receive_json())["event"]["generators"][0]
