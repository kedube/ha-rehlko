"""The JSON snapshot the sidebar panel renders: raw payloads, derived state, entity ids."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from ..const import DOMAIN
from ..models import GeneratorData

MAX_EVENTS = 300
MAX_NOTIFICATIONS = 100

# Most of a snapshot's size, and unchanged on almost every poll: the feeds are read every
# couple of minutes and the entity list changes only when entities do.
SELDOM_CHANGED = ("events", "notifications", "maintenance_notes", "entities")


def _derived(gen: GeneratorData) -> dict[str, Any]:
    return {
        "is_connected": gen.is_connected,
        "is_running": gen.is_running,
        "is_exercising": gen.is_exercising,
        "on_generator_power": gen.on_generator_power,
        "utility_present": gen.utility_present,
        "ready_to_run": gen.ready_to_run,
        "has_schedule": gen.has_schedule,
        "e_stop_engaged": gen.e_stop_engaged,
        "nominal_voltage": gen.nominal_voltage,
        "supports_exercise_scheduling": gen.supports_exercise_scheduling,
        "supports_next_exercise_datetime": gen.supports_next_exercise_datetime,
        "ip_address": gen.ip_address,
    }


def build_snapshot(hass: HomeAssistant) -> dict[str, Any]:
    registry = er.async_get(hass)
    generators: list[dict[str, Any]] = []
    accounts: list[dict[str, Any]] = []
    for entry in hass.config_entries.async_entries(DOMAIN):
        if entry.state is not ConfigEntryState.LOADED:
            accounts.append({"entry_id": entry.entry_id, "title": entry.title, "loaded": False})
            continue
        coordinator = entry.runtime_data
        data = coordinator.data
        if data is None:
            continue
        entity_ids: dict[str, dict[str, str]] = {}
        notify_entities: dict[str, str] = {}
        generator_prefix = f"{entry.entry_id}-"
        for ent in er.async_entries_for_config_entry(registry, entry.entry_id):
            if not ent.unique_id:
                continue
            if ent.unique_id.startswith(f"account-{entry.entry_id}-notify-"):
                # Account-wide notification switches, keyed by the API setting (e.g. sendShutdowns).
                notify_entities[ent.unique_id.rsplit("-notify-", 1)[1]] = ent.entity_id
            elif ent.unique_id.startswith(generator_prefix) and ent.disabled_by is None:
                # `{entry id}-{generator id}-{key}`, see entity.generator_unique_id.
                device_part, _, key = ent.unique_id.removeprefix(generator_prefix).partition("-")
                entity_ids.setdefault(device_part, {})[f"{ent.domain}.{key}"] = ent.entity_id
        accounts.append(
            {
                "entry_id": entry.entry_id,
                "title": entry.title,
                "loaded": True,
                "last_update_success": coordinator.last_update_success,
                "notification_settings": data.notification_settings,
                "notification_entities": notify_entities,
                "me": {
                    k: data.me.get(k) for k in ("firstName", "lastName", "email") if k in data.me
                },
            }
        )
        for device_id, gen in data.generators.items():
            generators.append(
                {
                    "entry_id": entry.entry_id,
                    "device_id": device_id,
                    "available": coordinator.last_update_success and gen.details_available,
                    "ha_device_id": coordinator.ha_device_id(gen),
                    "name": gen.name,
                    "serial_number": gen.serial_number,
                    "home": {k: v for k, v in gen.home.items() if k != "devices"},
                    "device": gen.device,
                    "details": gen.details,
                    "alerts": gen.alerts,
                    "events": gen.events[:MAX_EVENTS],
                    "maintenance_notes": gen.maintenance_notes,
                    "notifications": gen.notifications[:MAX_NOTIFICATIONS],
                    "cell_plan": gen.cell_plan,
                    "derived": _derived(gen),
                    "entities": entity_ids.get(str(device_id), {}),
                    "details_updated": gen.details_updated.isoformat()
                    if gen.details_updated
                    else None,
                    "feeds_updated": gen.feeds_updated.isoformat() if gen.feeds_updated else None,
                }
            )
    return {"generators": generators, "accounts": accounts}


def trim_snapshot(snapshot: dict[str, Any], sent: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """`snapshot` without the bulky fields a subscriber already has.

    `sent` is that subscriber's memory of what it last received, per generator; it is updated
    here. A field left out means "unchanged": the panel keeps the copy it has. The first
    snapshot for a generator is always complete.
    """
    generators = []
    current = set()
    for generator in snapshot["generators"]:
        key = f"{generator['entry_id']}:{generator['device_id']}"
        current.add(key)
        last = sent.setdefault(key, {})
        slim = dict(generator)
        for name in SELDOM_CHANGED:
            if name in last and last[name] == generator[name]:
                del slim[name]
            else:
                last[name] = generator[name]
        generators.append(slim)
    for key in set(sent) - current:
        del sent[key]
    return {**snapshot, "generators": generators}
