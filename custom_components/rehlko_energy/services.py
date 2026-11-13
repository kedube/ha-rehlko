"""Domain services: exercise control, maintenance notes, clock, peripherals, data queries."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import (
    HomeAssistant,
    ServiceCall,
    ServiceResponse,
    SupportsResponse,
    callback,
)
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.service import async_register_admin_service
from homeassistant.util import dt as dt_util

from .api.util import slugify
from .const import (
    DOMAIN,
    EXERCISE_FREQUENCIES,
    EXERCISE_MAX_MINUTES,
    EXERCISE_MIN_MINUTES,
    EXERCISE_MODES,
)
from .coordinator import RehlkoCoordinator, describe_event, describe_notification

ATTR_DEVICE_ID = "device_id"
_MODES = {slugify(v): v for v in EXERCISE_MODES}
_FREQUENCIES = {slugify(v): v for v in EXERCISE_FREQUENCIES}


def _wire(mapping: dict[str, str]) -> vol.Any:
    """Accept either the option slug (`unloaded_full_speed`) or the wire value."""
    wires = {v.lower(): v for v in mapping.values()}

    def _coerce(value: Any) -> str:
        text = str(value).strip()
        if text in mapping:
            return mapping[text]
        if text.lower() in wires:
            return wires[text.lower()]
        raise vol.Invalid(f"Expected one of {', '.join(mapping)}")

    return _coerce


BASE = {vol.Required(ATTR_DEVICE_ID): cv.string}
SCHEMAS: dict[str, vol.Schema] = {
    "start_exercise": vol.Schema({**BASE, vol.Optional("mode"): _wire(_MODES)}),
    "stop_exercise": vol.Schema(BASE),
    "set_exercise_schedule": vol.Schema(
        {
            **BASE,
            vol.Optional("frequency"): _wire(_FREQUENCIES),
            vol.Optional("mode"): _wire(_MODES),
            vol.Optional("duration"): vol.All(
                vol.Coerce(int), vol.Range(EXERCISE_MIN_MINUTES, EXERCISE_MAX_MINUTES)
            ),
            vol.Optional("next_start"): cv.datetime,
        }
    ),
    "delete_exercise_schedule": vol.Schema(BASE),
    "add_maintenance_note": vol.Schema(
        {**BASE, vol.Required("note"): vol.All(cv.string, vol.Length(min=1, max=2000))}
    ),
    "sync_controller_clock": vol.Schema({**BASE, vol.Optional("timestamp"): cv.datetime}),
    "set_peripheral_value": vol.Schema(
        {
            **BASE,
            vol.Required("definition_id"): cv.string,
            vol.Required("value"): vol.Any(bool, int, float, cv.string),
        }
    ),
    "rename_peripheral": vol.Schema(
        {
            **BASE,
            vol.Required("definition_id"): cv.string,
            vol.Required("name"): vol.All(cv.string, vol.Length(min=1, max=64)),
        }
    ),
    "refresh": vol.Schema({vol.Optional(ATTR_DEVICE_ID): cv.string}),
    "get_activity_log": vol.Schema(
        {**BASE, vol.Optional("limit", default=100): vol.All(vol.Coerce(int), vol.Range(1, 1000))}
    ),
    "get_alerts": vol.Schema(BASE),
    "get_maintenance_history": vol.Schema(BASE),
    "get_notifications": vol.Schema(
        {**BASE, vol.Optional("limit", default=50): vol.All(vol.Coerce(int), vol.Range(1, 500))}
    ),
    "get_generator_data": vol.Schema(BASE),
    "get_parameter_definitions": vol.Schema(
        {**BASE, vol.Required("kind", default="generator"): vol.In(["generator", "ats"])}
    ),
}


def resolve(hass: HomeAssistant, device_id: str) -> tuple[RehlkoCoordinator, int]:
    """Map a Home Assistant device (generator or its transfer switch) to its coordinator."""
    device = dr.async_get(hass).async_get(device_id)
    if device is None:
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="device_not_found",
            translation_placeholders={"device_id": device_id},
        )
    generator_id: int | None = None
    for domain, identifier in device.identifiers:
        if domain == DOMAIN and not identifier.startswith("account:"):
            base = identifier.split(":", 1)[0]
            if base.isdigit():
                generator_id = int(base)
    if generator_id is None:
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="not_a_generator",
            translation_placeholders={"device_id": device_id},
        )
    for entry_id in device.config_entries:
        entry = hass.config_entries.async_get_entry(entry_id)
        if entry and entry.domain == DOMAIN and entry.state is ConfigEntryState.LOADED:
            return entry.runtime_data, generator_id
    raise ServiceValidationError(
        translation_domain=DOMAIN,
        translation_key="entry_not_loaded",
        translation_placeholders={"device_id": device_id},
    )


@callback
def async_setup_services(hass: HomeAssistant) -> None:
    async def start_exercise(call: ServiceCall) -> None:
        coordinator, gid = resolve(hass, call.data[ATTR_DEVICE_ID])
        await coordinator.async_start_exercise(gid, call.data.get("mode"))

    async def stop_exercise(call: ServiceCall) -> None:
        coordinator, gid = resolve(hass, call.data[ATTR_DEVICE_ID])
        await coordinator.async_stop_exercise(gid)

    async def set_exercise_schedule(call: ServiceCall) -> None:
        coordinator, gid = resolve(hass, call.data[ATTR_DEVICE_ID])
        next_start = call.data.get("next_start")
        if next_start is not None and next_start.tzinfo is None:
            next_start = next_start.replace(tzinfo=dt_util.get_default_time_zone())
        await coordinator.async_set_exercise_schedule(
            gid,
            frequency=call.data.get("frequency"),
            mode=call.data.get("mode"),
            duration_minutes=call.data.get("duration"),
            next_start=next_start,
        )

    async def delete_exercise_schedule(call: ServiceCall) -> None:
        coordinator, gid = resolve(hass, call.data[ATTR_DEVICE_ID])
        await coordinator.async_delete_exercise_schedule(gid)

    async def add_maintenance_note(call: ServiceCall) -> None:
        coordinator, gid = resolve(hass, call.data[ATTR_DEVICE_ID])
        await coordinator.async_add_maintenance_note(gid, call.data["note"])

    async def sync_controller_clock(call: ServiceCall) -> None:
        coordinator, gid = resolve(hass, call.data[ATTR_DEVICE_ID])
        when = call.data.get("timestamp")
        if when is not None and when.tzinfo is None:
            when = when.replace(tzinfo=dt_util.get_default_time_zone())
        await coordinator.async_sync_controller_clock(gid, when)

    async def set_peripheral_value(call: ServiceCall) -> None:
        coordinator, gid = resolve(hass, call.data[ATTR_DEVICE_ID])
        await coordinator.async_set_peripheral_value(
            gid, call.data["definition_id"], call.data["value"]
        )

    async def rename_peripheral(call: ServiceCall) -> None:
        coordinator, gid = resolve(hass, call.data[ATTR_DEVICE_ID])
        await coordinator.async_rename_peripheral(
            gid, call.data["definition_id"], call.data["name"]
        )

    async def refresh(call: ServiceCall) -> None:
        if call.data.get(ATTR_DEVICE_ID):
            coordinator, _ = resolve(hass, call.data[ATTR_DEVICE_ID])
            await coordinator.async_refresh_everything()
            return
        for entry in hass.config_entries.async_loaded_entries(DOMAIN):
            await entry.runtime_data.async_refresh_everything()

    async def get_activity_log(call: ServiceCall) -> ServiceResponse:
        coordinator, gid = resolve(hass, call.data[ATTR_DEVICE_ID])
        gen = coordinator.generator(gid)
        return {"events": [describe_event(e) for e in gen.events[: call.data["limit"]]]}

    async def get_alerts(call: ServiceCall) -> ServiceResponse:
        coordinator, gid = resolve(hass, call.data[ATTR_DEVICE_ID])
        return {"alerts": [describe_event(a) for a in coordinator.generator(gid).alerts]}

    async def get_maintenance_history(call: ServiceCall) -> ServiceResponse:
        coordinator, gid = resolve(hass, call.data[ATTR_DEVICE_ID])
        gen = coordinator.generator(gid)
        return {
            "notes": [
                {
                    "id": n.get("id"),
                    "timestamp": n.get("timestamp"),
                    "contents": n.get("contents"),
                    "by_dealer": n.get("authorIsDealer"),
                    "author": n.get("dealerAuthor"),
                }
                for n in gen.maintenance_notes
            ],
            "last_maintenance": gen.device.get("lastMaintenanceTimestamp"),
            "next_maintenance": gen.device.get("nextMaintenanceTimestamp"),
            "maintenance_period_days": gen.device.get("maintenancePeriodDays"),
            "runtime_since_maintenance_hours": gen.details.get("runtimeSinceLastMaintenanceHours"),
        }

    async def get_notifications(call: ServiceCall) -> ServiceResponse:
        coordinator, gid = resolve(hass, call.data[ATTR_DEVICE_ID])
        gen = coordinator.generator(gid)
        return {
            "notifications": [
                describe_notification(n) for n in gen.notifications[: call.data["limit"]]
            ]
        }

    async def get_generator_data(call: ServiceCall) -> ServiceResponse:
        coordinator, gid = resolve(hass, call.data[ATTR_DEVICE_ID])
        gen = coordinator.generator(gid)
        return {
            "device": gen.device,
            "details": gen.details,
            "home": {k: v for k, v in gen.home.items() if k != "devices"},
        }

    async def get_parameter_definitions(call: ServiceCall) -> ServiceResponse:
        coordinator, gid = resolve(hass, call.data[ATTR_DEVICE_ID])
        gen = coordinator.generator(gid)
        if call.data["kind"] == "ats":
            serial, kind = gen.ats.get("serialNumber"), "ats"
        else:
            serial = (
                gen.generators[0].get("serialNumber") if gen.generators else None
            ) or gen.serial_number
            kind = "generators"
        if not serial:
            raise ServiceValidationError(translation_domain=DOMAIN, translation_key="no_serial")
        definitions = await coordinator.async_get_parameter_definitions(gid, kind, serial)
        return {"definitions": definitions if isinstance(definitions, (list, dict)) else []}

    handlers = {
        "start_exercise": (start_exercise, SupportsResponse.NONE),
        "stop_exercise": (stop_exercise, SupportsResponse.NONE),
        "set_exercise_schedule": (set_exercise_schedule, SupportsResponse.NONE),
        "delete_exercise_schedule": (delete_exercise_schedule, SupportsResponse.NONE),
        "add_maintenance_note": (add_maintenance_note, SupportsResponse.NONE),
        "sync_controller_clock": (sync_controller_clock, SupportsResponse.NONE),
        "set_peripheral_value": (set_peripheral_value, SupportsResponse.NONE),
        "rename_peripheral": (rename_peripheral, SupportsResponse.NONE),
        "refresh": (refresh, SupportsResponse.NONE),
        "get_activity_log": (get_activity_log, SupportsResponse.ONLY),
        "get_alerts": (get_alerts, SupportsResponse.ONLY),
        "get_maintenance_history": (get_maintenance_history, SupportsResponse.ONLY),
        "get_notifications": (get_notifications, SupportsResponse.ONLY),
        "get_generator_data": (get_generator_data, SupportsResponse.ONLY),
        "get_parameter_definitions": (get_parameter_definitions, SupportsResponse.ONLY),
    }
    for name, (handler, response) in handlers.items():
        async_register_admin_service(
            hass, DOMAIN, name, handler, schema=SCHEMAS[name], supports_response=response
        )
