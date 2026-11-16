"""Exercise the integration lifecycle against Home Assistant, without the cloud."""

import asyncio
import json
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import callback
from homeassistant.exceptions import ConfigEntryNotReady, HomeAssistantError
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.rehlko_energy import (
    async_remove_config_entry_device,
    async_setup_entry,
    build_client,
)
from custom_components.rehlko_energy.api import AppCredentials, RehlkoConnectionError
from custom_components.rehlko_energy.const import DOMAIN, EVENT_POWER
from custom_components.rehlko_energy.coordinator import FEED_NOTIFICATION, RehlkoCoordinator
from custom_components.rehlko_energy.models import AccountData
from custom_components.rehlko_energy.sidebar import (
    BUNDLE,
    STATIC_ROOT,
    STATIC_URL,
    URL_PATH,
    async_setup_sidebar,
)
from custom_components.rehlko_energy.sidebar.snapshot import build_snapshot

from .conftest import FakeResponse, FakeSession, standby, token_response
from .test_entities import SAMPLE_DETAILS, SAMPLE_DEVICE, build_sample_gen


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
        assert snapshot["generators"][0]["derived"]["mac_address"] == "aa:bb:cc:dd:ee:ff"
        assert snapshot["generators"][0]["derived"]["load_w"] == 5400
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
    # The product photos are files beside the script, which finds them by its own URL.
    photos = sorted((BUNDLE.parent / "assets").glob("generator-*.webp"))
    assert len(photos) == 4
    for photo in photos:
        assert f"assets/{photo.name}" in BUNDLE.read_text(encoding="utf-8")
        response = await http.get(f"{STATIC_ROOT}/assets/{photo.name}")
        assert response.status == 200
        assert response.content_type == "image/webp"
        assert await response.read() == photo.read_bytes()


async def test_failed_initial_feeds_do_not_announce_historical_items(hass, entry, client):
    client.get_events.side_effect = RehlkoConnectionError("temporary failure")
    with patch(MONOTONIC, return_value=5000.0) as clock:
        coordinator = RehlkoCoordinator(hass, entry, client)
        with patch.object(coordinator, "_fire") as fire:
            coordinator.data = await coordinator._async_update_data()
            client.get_events.side_effect = None
            client.get_events.return_value = [{"id": 1, "timestamp": "2026-01-01T00:00:00Z"}]
            clock.return_value += 60  # the next standby poll tries the failed feed again
            coordinator.data = await coordinator._async_update_data()
            await hass.async_block_till_done()
            fire.assert_not_called()
            client.get_events.return_value.insert(0, {"id": 2, "timestamp": "2026-01-02T00:00:00Z"})
            coordinator._force_feeds.add(1)
            coordinator.data = await coordinator._async_update_data()
            await hass.async_block_till_done()
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


# ---- forced re-reads, feed scheduling, announcements ---------------------------------------


@pytest.mark.parametrize("uptime", UPTIMES)
async def test_refresh_reads_the_account_again_however_recently_the_host_booted(
    hass, entry, client, uptime
):
    with patch(MONOTONIC, return_value=uptime):
        coordinator = RehlkoCoordinator(hass, entry, client)
        await coordinator.async_refresh()
        client.get_me.reset_mock()
        client.get_notification_settings.reset_mock()
        await coordinator.async_refresh_everything()  # the Refresh button and action
    client.get_me.assert_awaited_once()
    client.get_notification_settings.assert_awaited_once()


@pytest.mark.parametrize("uptime", UPTIMES)
async def test_a_notification_change_is_read_back_however_recently_the_host_booted(
    hass, entry, client, uptime
):
    client.set_notification_settings = AsyncMock(return_value=None)
    with patch(MONOTONIC, return_value=uptime):
        coordinator = RehlkoCoordinator(hass, entry, client)
        await coordinator.async_refresh()
        client.get_notification_settings.reset_mock()
        await coordinator.async_set_notification_setting("sendShutdowns", False)
        await hass.async_block_till_done()
    client.get_notification_settings.assert_awaited()


async def test_one_generators_failing_feed_leaves_the_others_on_their_interval(hass, entry, client):
    client.get_homes.return_value[0]["devices"].append({**SAMPLE_DEVICE, "id": 2})
    standby(client)

    async def notifications(*, device_id=None, offset=0, limit=50):
        if device_id == 2:
            raise RehlkoConnectionError("notifications down for this generator")
        return []

    client.get_notifications.side_effect = notifications
    with patch(MONOTONIC, return_value=5000.0) as clock:
        coordinator = RehlkoCoordinator(hass, entry, client)
        coordinator.data = await coordinator._async_update_data()
        client.get_events.reset_mock()
        for elapsed in (60, 90, 110):  # standby polls inside the two-minute feed interval
            clock.return_value = 5000.0 + elapsed
            coordinator.data = await coordinator._async_update_data()
    read = [call.args[0] for call in client.get_events.await_args_list]
    assert read == [2]  # only the failing generator, once, at the next poll


async def test_a_feed_that_keeps_failing_is_read_no_more_often_than_one_that_works(
    hass, entry, client
):
    standby(client)
    client.get_notifications.side_effect = RehlkoConnectionError("notifications down")
    reads = []
    with patch(MONOTONIC, return_value=5000.0) as clock:
        coordinator = RehlkoCoordinator(hass, entry, client)
        coordinator.data = await coordinator._async_update_data()
        for elapsed in range(60, 660, 60):  # ten standby polls, a minute apart
            clock.return_value = 5000.0 + elapsed
            client.get_notifications.reset_mock()
            coordinator.data = await coordinator._async_update_data()
            reads.append(client.get_notifications.await_count)
    # Tried again at the next poll, then every other poll: the two-minute feed interval.
    assert reads == [1, 0, 1, 0, 1, 0, 1, 0, 1, 0]


async def test_a_generator_whose_details_keep_failing_is_not_read_in_full_every_poll(
    hass, entry, client
):
    standby(client)
    client.get_device.side_effect = RehlkoConnectionError("details down")
    with patch(MONOTONIC, return_value=5000.0) as clock:
        coordinator = RehlkoCoordinator(hass, entry, client)
        coordinator.data = await coordinator._async_update_data()
        client.get_maintenance_notes.assert_awaited_once()
        for elapsed in (60, 120, 180):
            clock.return_value = 5000.0 + elapsed
            coordinator.data = await coordinator._async_update_data()
    client.get_maintenance_notes.assert_awaited_once()  # next due with the account's 15 min


async def test_the_account_is_read_alongside_the_generators(hass, entry, client):
    account_started = asyncio.Event()

    async def details(*_args):
        # Waits for the account read: it would time out if that came after the generators.
        await asyncio.wait_for(account_started.wait(), 1)
        return deepcopy(SAMPLE_DETAILS)

    async def me():
        account_started.set()
        return {"id": "owner"}

    client.get_device.side_effect = details
    client.get_me.side_effect = me
    coordinator = RehlkoCoordinator(hass, entry, client)
    coordinator.data = await coordinator._async_update_data()
    assert coordinator.data.me == {"id": "owner"}
    assert coordinator.data.generators[1].details_available


async def test_raising_the_notification_limit_announces_no_old_notifications(hass, client):
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Test account",
        unique_id="owner",
        data={},
        options={"notification_limit": 10},
    )
    entry.add_to_hass(hass)
    newest = datetime(2026, 11, 1, tzinfo=UTC)

    def page(*, device_id=None, offset=0, limit=50):
        return [
            {
                "id": 9000 - i,
                "type": "EngineStartedNotice",
                "timestamp": (newest - timedelta(hours=i)).isoformat(),
            }
            for i in range(limit)
        ]

    def announced(fire) -> list:
        return [
            c.args[0].item["id"] for c in fire.call_args_list if c.args[0].feed == FEED_NOTIFICATION
        ]

    client.get_notifications.side_effect = page
    with patch(MONOTONIC, return_value=5000.0):
        coordinator = RehlkoCoordinator(hass, entry, client)
        coordinator.data = await coordinator._async_update_data()  # sees the newest ten
        with patch.object(coordinator, "_fire") as fire:
            # The option now keeps fifty (the entry reloads; what was seen is kept).
            coordinator._notification_limit = 50
            coordinator._force_feeds.add(1)
            coordinator.data = await coordinator._async_update_data()
            await hass.async_block_till_done()
            assert announced(fire) == []

            later = {
                "id": 9001,
                "type": "EngineStoppedNotice",
                "timestamp": (newest + timedelta(hours=1)).isoformat(),
            }
            client.get_notifications.side_effect = lambda **kw: [later, *page(**kw)[:-1]]
            coordinator._force_feeds.add(1)
            coordinator.data = await coordinator._async_update_data()
            await hass.async_block_till_done()
            assert announced(fire) == [9001]


async def test_listeners_see_the_states_an_event_describes(
    hass, entry, client, enable_custom_integrations
):
    with patch("custom_components.rehlko_energy.build_client", return_value=client):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    power_source = er.async_get(hass).async_get_entity_id(
        "sensor", DOMAIN, f"{entry.entry_id}-1-power_source"
    )
    assert hass.states.get(power_source).state == "generator"
    seen = []

    @callback
    def listener(event) -> None:
        seen.append((event.data["type"], hass.states.get(power_source).state))

    hass.bus.async_listen(EVENT_POWER, listener)
    standby(client)  # utility is back and the generator has stopped
    await entry.runtime_data.async_refresh()
    await hass.async_block_till_done()
    assert ("utility_restored", "utility") in seen
    assert {state for _, state in seen} == {"utility"}


# ---- privacy -------------------------------------------------------------------------------


async def test_the_accounts_email_stays_out_of_entity_ids_and_names(
    hass, client, enable_custom_integrations
):
    entry = MockConfigEntry(
        domain=DOMAIN, title="pat.owner@example.com", unique_id="owner", data={}
    )
    entry.add_to_hass(hass)
    with patch("custom_components.rehlko_energy.build_client", return_value=client):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    account = [
        ent
        for ent in er.async_entries_for_config_entry(er.async_get(hass), entry.entry_id)
        if ent.unique_id.startswith("account-")
    ]
    assert account
    for ent in account:
        assert "example" not in ent.entity_id
        assert "example.com" not in hass.states.get(ent.entity_id).attributes["friendly_name"]
    device = dr.async_get(hass).async_get(account[0].device_id)
    assert device.name == "Rehlko account"


async def test_free_text_sensors_start_disabled(hass, entry, client, enable_custom_integrations):
    client.get_maintenance_notes.return_value = [{"id": 1, "contents": "Called Pat on 555-0100"}]
    client.get_notifications.return_value = [{"id": 7, "message": "Home Generator (SN123) ran"}]
    with patch("custom_components.rehlko_energy.build_client", return_value=client):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    registry = er.async_get(hass)
    for key in ("last_maintenance_note", "last_notification", "dealer"):
        entity_id = registry.async_get_entity_id("sensor", DOMAIN, f"{entry.entry_id}-1-{key}")
        assert entity_id, key
        assert registry.async_get(entity_id).disabled_by is er.RegistryEntryDisabler.INTEGRATION
        assert hass.states.get(entity_id) is None


# ---- the panel -----------------------------------------------------------------------------


async def test_open_panels_share_one_snapshot_per_poll(
    hass, entry, client, enable_custom_integrations, hass_ws_client
):
    with patch("custom_components.rehlko_energy.build_client", return_value=client):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    panels = []
    for _ in range(3):
        ws = await hass_ws_client(hass)
        await ws.send_json({"id": 1, "type": f"{DOMAIN}/subscribe"})
        assert (await ws.receive_json())["success"]
        assert (await ws.receive_json())["event"]["generators"]
        panels.append(ws)
    with patch(
        "custom_components.rehlko_energy.sidebar.commands.build_snapshot", wraps=build_snapshot
    ) as build:
        await entry.runtime_data.async_refresh()
        for ws in panels:
            assert (await ws.receive_json())["event"]["generators"][0]["device_id"] == 1
    assert build.call_count == 1


async def test_the_definitions_command_only_reads_this_accounts_controllers(
    hass, entry, client, enable_custom_integrations, hass_ws_client
):
    with patch("custom_components.rehlko_energy.build_client", return_value=client):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    client.get_parameter_definitions = AsyncMock(return_value=[{"id": 7}])
    ws = await hass_ws_client(hass)
    base = {
        "type": f"{DOMAIN}/definitions",
        "entry_id": entry.entry_id,
        "device_id": 1,
        "kind": "generators",
    }
    await ws.send_json({"id": 1, **base, "serial_number": "SOMEONE-ELSES"})
    response = await ws.receive_json()
    assert response["error"]["code"] == "not_found"
    await ws.send_json({"id": 2, **base, "serial_number": "GEN1"})
    response = await ws.receive_json()
    assert response["result"] == {"definitions": [{"id": 7}]}
    await ws.send_json({"id": 3, **base, "kind": "ats", "serial_number": "ATS1"})
    assert (await ws.receive_json())["success"]
    await ws.send_json({"id": 4, **base, "device_id": 99, "serial_number": "GEN1"})
    assert (await ws.receive_json())["error"]["code"] == "failed"
    client.get_parameter_definitions.assert_any_await(1, "generators", "GEN1")
    client.get_parameter_definitions.assert_any_await(1, "ats", "ATS1")


# ---- lifecycle -----------------------------------------------------------------------------


async def test_only_devices_of_generators_that_left_can_be_removed(
    hass, entry, client, enable_custom_integrations
):
    with patch("custom_components.rehlko_energy.build_client", return_value=client):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    registry = dr.async_get(hass)
    devices = {
        identifier: device
        for device in dr.async_entries_for_config_entry(registry, entry.entry_id)
        for domain, identifier in device.identifiers
        if domain == DOMAIN
    }
    gone = registry.async_get_or_create(
        config_entry_id=entry.entry_id, identifiers={(DOMAIN, "99")}
    )
    for kept in ("1", "1:ats", f"account:{entry.entry_id}"):
        assert not await async_remove_config_entry_device(hass, entry, devices[kept])
    assert await async_remove_config_entry_device(hass, entry, gone)


async def test_saving_options_reloads_with_them(hass, entry, client, enable_custom_integrations):
    with patch("custom_components.rehlko_energy.build_client", return_value=client):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        first = entry.runtime_data
        flow = await hass.config_entries.options.async_init(entry.entry_id)
        result = await hass.config_entries.options.async_configure(
            flow["flow_id"],
            {
                "scan_interval": 30.0,
                "active_scan_interval": 15.0,
                "feed_interval": 120.0,
                "notification_limit": 50.0,
                "sidebar_panel": True,
                "extra_diagnostic_entities": True,
            },
        )
        await hass.async_block_till_done()
    assert result["type"] == "create_entry"
    assert entry.options["scan_interval"] == 30
    assert type(entry.options["scan_interval"]) is int
    assert entry.runtime_data is not first
    assert entry.runtime_data.longest_interval == timedelta(seconds=30)


async def test_a_new_refresh_token_is_saved_without_a_reload(
    hass, client, enable_custom_integrations
):
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Test account",
        unique_id="owner",
        data={"username": "owner@example.com", "password": "pw", "refresh_token": "old"},
    )
    entry.add_to_hass(hass)
    with patch("custom_components.rehlko_energy.build_client", return_value=client):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    coordinator = entry.runtime_data
    session = FakeSession(
        {("POST", "/token"): FakeResponse(200, token_response(refresh_token="new"))}
    )
    with patch("custom_components.rehlko_energy.async_get_clientsession", return_value=session):
        real = build_client(hass, entry, AppCredentials("id", "secret", "key"))
    await real.auth.async_get_access_token()
    await hass.async_block_till_done()
    assert entry.data["refresh_token"] == "new"
    assert entry.runtime_data is coordinator
