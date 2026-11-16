"""Websocket commands for the sidebar panel.

`rehlko_energy/subscribe` pushes a full snapshot now, then one after every poll of any account
with the bulky, seldom-changed fields left out unless they changed (see `trim_snapshot`);
`rehlko_energy/definitions` fetches a controller's parameter catalogue on demand. Actions
go through the domain's services, so the panel and automations share one code path.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.config_entries import SIGNAL_CONFIG_ENTRY_CHANGED, ConfigEntryState
from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.util.hass_dict import HassKey

from ..const import DOMAIN
from .snapshot import build_snapshot, trim_snapshot

_LOGGER = logging.getLogger(__name__)

type Push = Callable[[dict[str, Any]], None]


class SnapshotHub:
    """Builds one snapshot per poll and hands it to every open panel.

    It listens to the accounts only while a panel is subscribed.
    """

    def __init__(self, hass: HomeAssistant) -> None:
        self._hass = hass
        self._subscribers: list[Push] = []
        self._listeners: list[CALLBACK_TYPE] = []
        self._unsub_entries: CALLBACK_TYPE | None = None

    @callback
    def async_add(self, push: Push) -> CALLBACK_TYPE:
        """Call `push` with each new snapshot until the returned callback is called."""
        if not self._subscribers:
            self._unsub_entries = async_dispatcher_connect(
                self._hass, SIGNAL_CONFIG_ENTRY_CHANGED, self._entry_changed
            )
            self._attach()
        self._subscribers.append(push)

        @callback
        def _remove() -> None:
            if push in self._subscribers:
                self._subscribers.remove(push)
            if not self._subscribers:
                self._detach()
                if self._unsub_entries is not None:
                    self._unsub_entries()
                    self._unsub_entries = None

        return _remove

    @callback
    def _attach(self) -> None:
        self._detach()
        for entry in self._hass.config_entries.async_loaded_entries(DOMAIN):
            self._listeners.append(entry.runtime_data.async_add_listener(self._publish))

    @callback
    def _detach(self) -> None:
        while self._listeners:
            self._listeners.pop()()

    @callback
    def _entry_changed(self, _change: Any, entry: Any) -> None:
        if entry.domain == DOMAIN:
            self._attach()
            self._publish()

    @callback
    def _publish(self) -> None:
        if not self._subscribers:
            return
        try:
            snapshot = build_snapshot(self._hass)
        except Exception:
            # Raised inside the coordinator's update, it would stop the entities after it.
            _LOGGER.exception("Could not build the panel's snapshot")
            return
        for push in list(self._subscribers):
            push(snapshot)


DATA_SNAPSHOTS: HassKey[SnapshotHub] = HassKey(f"{DOMAIN}_snapshots")


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
    sent: dict[str, dict[str, Any]] = {}  # what this subscriber already has, per generator

    @callback
    def _push(snapshot: dict[str, Any]) -> None:
        connection.send_message(
            websocket_api.event_message(msg["id"], trim_snapshot(snapshot, sent))
        )

    hub = hass.data.get(DATA_SNAPSHOTS)
    if hub is None:
        hub = hass.data[DATA_SNAPSHOTS] = SnapshotHub(hass)
    connection.subscriptions[msg["id"]] = hub.async_add(_push)
    connection.send_result(msg["id"])
    _push(build_snapshot(hass))


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
