"""Websocket commands for the sidebar panel.

`rehlko_energy/subscribe` pushes a full snapshot now, then one after every poll of any account
with the bulky, seldom-changed fields left out unless they changed (see `trim_snapshot`);
`rehlko_energy/definitions` fetches a controller's parameter catalogue on demand. Actions
go through the domain's services, so the panel and automations share one code path.
"""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.config_entries import SIGNAL_CONFIG_ENTRY_CHANGED, ConfigEntryState
from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from ..const import DOMAIN
from .snapshot import build_snapshot, trim_snapshot


@callback
def async_register_commands(hass: HomeAssistant) -> None:
    websocket_api.async_register_command(hass, ws_subscribe)
    websocket_api.async_register_command(hass, ws_snapshot)
    websocket_api.async_register_command(hass, ws_definitions)


@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/snapshot"})
@websocket_api.require_admin
@callback
def ws_snapshot(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    connection.send_result(msg["id"], build_snapshot(hass))


@websocket_api.websocket_command({vol.Required("type"): f"{DOMAIN}/subscribe"})
@websocket_api.require_admin
@callback
def ws_subscribe(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    listeners: list[CALLBACK_TYPE] = []
    sent: dict[str, dict[str, Any]] = {}  # what this subscriber already has, per generator

    @callback
    def _send() -> None:
        snapshot = trim_snapshot(build_snapshot(hass), sent)
        connection.send_message(websocket_api.event_message(msg["id"], snapshot))

    @callback
    def _attach() -> None:
        while listeners:
            listeners.pop()()
        for entry in hass.config_entries.async_loaded_entries(DOMAIN):
            listeners.append(entry.runtime_data.async_add_listener(_send))

    @callback
    def _entry_changed(_change: Any, entry: Any) -> None:
        if entry.domain == DOMAIN:
            _attach()
            _send()

    unsub_entries = async_dispatcher_connect(hass, SIGNAL_CONFIG_ENTRY_CHANGED, _entry_changed)

    @callback
    def _unsubscribe() -> None:
        unsub_entries()
        while listeners:
            listeners.pop()()

    connection.subscriptions[msg["id"]] = _unsubscribe
    _attach()
    connection.send_result(msg["id"])
    _send()


@websocket_api.websocket_command(
    {
        vol.Required("type"): f"{DOMAIN}/definitions",
        vol.Required("entry_id"): str,
        vol.Required("device_id"): int,
        vol.Required("kind"): vol.In(["generators", "ats"]),
        vol.Required("serial_number"): str,
    }
)
@websocket_api.require_admin
@websocket_api.async_response
async def ws_definitions(
    hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]
) -> None:
    entry = hass.config_entries.async_get_entry(msg["entry_id"])
    if entry is None or entry.domain != DOMAIN or entry.state is not ConfigEntryState.LOADED:
        connection.send_error(msg["id"], "not_found", "Account not loaded")
        return
    try:
        gen = entry.runtime_data.generator(msg["device_id"])
        serials = (
            {str(gen.ats.get("serialNumber"))}
            if msg["kind"] == "ats"
            else {str(g.get("serialNumber")) for g in gen.generators} | {str(gen.serial_number)}
        )
        if not msg["serial_number"] or msg["serial_number"] not in serials - {"None", ""}:
            connection.send_error(msg["id"], "not_found", "Controller not found on this account")
            return
        result = await entry.runtime_data.async_get_parameter_definitions(
            msg["device_id"], msg["kind"], msg["serial_number"]
        )
    except HomeAssistantError as err:
        connection.send_error(msg["id"], "failed", str(err))
        return
    connection.send_result(msg["id"], {"definitions": result})
