"""WebSocket authorization, streaming cleanup and sidebar lifecycle."""

from unittest.mock import MagicMock, patch

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import Context
from homeassistant.exceptions import Unauthorized
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.rehlko_energy.const import CONF_SIDEBAR_PANEL, DOMAIN
from custom_components.rehlko_energy.services import async_setup_services
from custom_components.rehlko_energy.sidebar import URL_PATH, async_setup_sidebar
from custom_components.rehlko_energy.sidebar.commands import async_register_commands


@pytest.mark.parametrize("command", ["snapshot", "subscribe", "definitions"])
async def test_websocket_commands_require_admin(hass, hass_ws_client, hass_read_only_user, command):
    async_register_commands(hass)
    refresh_token = await hass.auth.async_create_refresh_token(
        hass_read_only_user, client_id="http://example.test"
    )
    token = hass.auth.async_create_access_token(refresh_token)
    ws = await hass_ws_client(hass, token)
    message = {"id": 1, "type": f"{DOMAIN}/{command}"}
    if command == "definitions":
        message.update(entry_id="other-account", device_id=1, kind="generators", serial_number="x")
    await ws.send_json(message)
    response = await ws.receive_json()
    assert not response["success"]
    assert response["error"]["code"] == "unauthorized"


async def test_subscription_is_released(hass, hass_ws_client):
    entry = MockConfigEntry(domain=DOMAIN, title="Test", data={})
    entry.add_to_hass(hass)
    coordinator = MagicMock()
    coordinator.data = None
    unsubscribe = MagicMock()
    coordinator.async_add_listener.return_value = unsubscribe
    entry.runtime_data = coordinator
    entry._async_set_state(hass, ConfigEntryState.LOADED, None)
    async_register_commands(hass)
    ws = await hass_ws_client(hass)
    await ws.send_json({"id": 1, "type": f"{DOMAIN}/subscribe"})
    assert (await ws.receive_json())["success"]
    snapshot = await ws.receive_json()
    assert snapshot["type"] == "event"
    await ws.send_json({"id": 2, "type": "unsubscribe_events", "subscription": 1})
    assert (await ws.receive_json())["success"]
    unsubscribe.assert_called_once()


async def test_domain_services_reject_read_only_users(hass, hass_read_only_user):
    async_setup_services(hass)
    with pytest.raises(Unauthorized):
        await hass.services.async_call(
            DOMAIN, "refresh", {}, blocking=True, context=Context(user_id=hass_read_only_user.id)
        )


async def test_panel_tracks_options_and_entry_removal(hass):
    assert await async_setup_component(hass, "panel_custom", {})
    entry = MockConfigEntry(domain=DOMAIN, title="Test", data={})
    entry.add_to_hass(hass)
    await async_setup_sidebar(hass)
    assert URL_PATH in hass.data["frontend_panels"]
    hass.config_entries.async_update_entry(entry, options={CONF_SIDEBAR_PANEL: False})
    await hass.async_block_till_done()
    assert URL_PATH not in hass.data["frontend_panels"]
    hass.config_entries.async_update_entry(entry, options={CONF_SIDEBAR_PANEL: True})
    await hass.async_block_till_done()
    assert URL_PATH in hass.data["frontend_panels"]
    # No cloud requests are needed when removing an unloaded account.
    with patch("custom_components.rehlko_energy.async_remove_entry"):
        assert await hass.config_entries.async_remove(entry.entry_id)
    await hass.async_block_till_done()
    assert URL_PATH not in hass.data["frontend_panels"]


async def test_definitions_rejects_a_serial_from_another_device(hass, hass_ws_client):
    from custom_components.rehlko_energy.models import AccountData

    from .test_entities import build_sample_gen

    entry = MockConfigEntry(domain=DOMAIN, title="Test", data={})
    entry.add_to_hass(hass)
    coordinator = MagicMock()
    gen = build_sample_gen()
    coordinator.data = AccountData(generators={1: gen})
    coordinator.generator.return_value = gen
    entry.runtime_data = coordinator
    entry._async_set_state(hass, ConfigEntryState.LOADED, None)
    async_register_commands(hass)
    ws = await hass_ws_client(hass)
    await ws.send_json(
        {
            "id": 1,
            "type": f"{DOMAIN}/definitions",
            "entry_id": entry.entry_id,
            "device_id": 1,
            "kind": "generators",
            "serial_number": "another-owner",
        }
    )
    result = await ws.receive_json()
    assert not result["success"]
    assert result["error"]["code"] == "not_found"
    coordinator.async_get_parameter_definitions.assert_not_called()


def test_trimming_remembers_each_subscriber_and_forgets_removed_generators():
    from copy import deepcopy

    from custom_components.rehlko_energy.sidebar.snapshot import trim_snapshot

    generator = {
        "entry_id": "a",
        "device_id": 1,
        "details": {"batteryVoltageV": 13.6},
        "events": [{"id": 1}],
        "notifications": [],
        "maintenance_notes": [{"id": 9}],
        "entities": {"sensor.battery_voltage": "sensor.x"},
    }
    snapshot = {"accounts": [{"entry_id": "a"}], "generators": [generator]}
    sent: dict = {}
    assert trim_snapshot(snapshot, sent) == snapshot
    assert snapshot["generators"][0] is generator and "events" in generator  # input untouched

    again = trim_snapshot(deepcopy(snapshot), sent)
    assert again["generators"] == [
        {"entry_id": "a", "device_id": 1, "details": {"batteryVoltageV": 13.6}}
    ]
    assert again["accounts"] == snapshot["accounts"]

    emptied = deepcopy(snapshot)
    emptied["generators"][0]["maintenance_notes"] = []
    assert trim_snapshot(emptied, sent)["generators"][0]["maintenance_notes"] == []

    # Another subscriber has its own memory; a generator that left is forgotten.
    assert "events" in trim_snapshot(deepcopy(snapshot), {})["generators"][0]
    trim_snapshot({"accounts": [], "generators": []}, sent)
    assert sent == {}
