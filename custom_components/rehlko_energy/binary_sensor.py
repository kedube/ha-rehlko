"""Binary sensors: connectivity, power, running state and problem conditions."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util

from . import RehlkoConfigEntry
from .api.util import humanize, parse_timestamp
from .const import CONF_EXTRA_DIAGNOSTICS, DEFAULT_EXTRA_DIAGNOSTICS
from .coordinator import RehlkoCoordinator
from .entity import RehlkoEntity, value_or_none
from .models import GeneratorData

PARALLEL_UPDATES = 0


@dataclass(frozen=True, kw_only=True)
class RehlkoBinaryDescription(BinarySensorEntityDescription):
    value_fn: Callable[[GeneratorData], bool | None]
    exists_fn: Callable[[GeneratorData], bool] | None = None
    attrs_fn: Callable[[GeneratorData], dict[str, Any] | None] | None = None


def _maintenance_due(g: GeneratorData) -> bool | None:
    due = parse_timestamp(g.device.get("nextMaintenanceTimestamp"), dt_util.get_default_time_zone())
    return None if due is None else due <= dt_util.utcnow()


def _not_in_auto(g: GeneratorData) -> bool | None:
    state = g.details.get("switchState")
    if state in (None, "", "swaggerGeneratedUnknown"):
        return None
    return state != "Auto"


def _oil_problem(g: GeneratorData) -> bool | None:
    ok = g.details.get("engineOilPressureOk")
    return None if ok is None else not bool(ok)


def _critical(g: GeneratorData) -> bool:
    return any(a.get("isCriticalFault") for a in g.alerts)


BINARY_SENSORS: tuple[RehlkoBinaryDescription, ...] = (
    RehlkoBinaryDescription(
        key="connected",
        translation_key="connected",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda g: g.is_connected,
        attrs_fn=lambda g: {
            "last_connected": g.device.get("lastConnectedTimestamp"),
            "connection_type": g.get("connectionType"),
        },
    ),
    RehlkoBinaryDescription(
        key="utility_power",
        translation_key="utility_power",
        device_class=BinarySensorDeviceClass.POWER,
        value_fn=lambda g: g.utility_present,
        attrs_fn=lambda g: {
            "utility_voltage": g.details.get("utilityVoltageV"),
            "nominal_voltage": g.nominal_voltage,
        },
    ),
    RehlkoBinaryDescription(
        key="on_generator_power",
        translation_key="on_generator_power",
        value_fn=lambda g: (
            g.on_generator_power if g.details.get("powerSource") is not None else None
        ),
        exists_fn=lambda g: "powerSource" in g.details,
    ),
    RehlkoBinaryDescription(
        key="running",
        translation_key="running",
        device_class=BinarySensorDeviceClass.RUNNING,
        value_fn=lambda g: g.is_running,
        attrs_fn=lambda g: {
            "engine_state": g.engine_state,
            "engine_speed_rpm": g.details.get("engineSpeedRpm"),
        },
    ),
    RehlkoBinaryDescription(
        key="exercising",
        translation_key="exercising",
        device_class=BinarySensorDeviceClass.RUNNING,
        value_fn=lambda g: g.is_exercising,
        attrs_fn=lambda g: {"running_mode": g.exercise.get("runningMode")},
    ),
    RehlkoBinaryDescription(
        key="ready_to_run",
        translation_key="ready_to_run",
        value_fn=lambda g: g.ready_to_run if g.status else None,
    ),
    RehlkoBinaryDescription(
        key="not_in_auto",
        translation_key="not_in_auto",
        device_class=BinarySensorDeviceClass.PROBLEM,
        value_fn=_not_in_auto,
        attrs_fn=lambda g: {"switch_state": g.details.get("switchState")},
        exists_fn=lambda g: "switchState" in g.details,
    ),
    RehlkoBinaryDescription(
        key="oil_pressure_problem",
        translation_key="oil_pressure_problem",
        device_class=BinarySensorDeviceClass.PROBLEM,
        value_fn=_oil_problem,
        exists_fn=lambda g: "engineOilPressureOk" in g.details,
    ),
    RehlkoBinaryDescription(
        key="maintenance_due",
        translation_key="maintenance_due",
        device_class=BinarySensorDeviceClass.PROBLEM,
        value_fn=_maintenance_due,
        attrs_fn=lambda g: {
            "next_maintenance": g.device.get("nextMaintenanceTimestamp"),
            "runtime_since_maintenance_hours": g.details.get("runtimeSinceLastMaintenanceHours"),
        },
        exists_fn=lambda g: "nextMaintenanceTimestamp" in g.device,
    ),
    RehlkoBinaryDescription(
        key="active_alerts",
        translation_key="active_alerts",
        device_class=BinarySensorDeviceClass.PROBLEM,
        value_fn=lambda g: bool(g.alerts) or bool(g.device.get("alertCount")),
        attrs_fn=lambda g: {
            "alerts": [a.get("name") or humanize(a.get("deviceEventId")) for a in g.alerts[:20]]
        },
    ),
    RehlkoBinaryDescription(
        key="critical_fault",
        translation_key="critical_fault",
        device_class=BinarySensorDeviceClass.PROBLEM,
        value_fn=_critical,
    ),
    RehlkoBinaryDescription(
        key="e_stop",
        translation_key="e_stop",
        device_class=BinarySensorDeviceClass.SAFETY,
        value_fn=lambda g: g.e_stop_engaged,
    ),
    RehlkoBinaryDescription(
        key="exercise_scheduled",
        translation_key="exercise_scheduled",
        value_fn=lambda g: g.has_schedule,
        exists_fn=lambda g: "exercise" in g.details,
    ),
    RehlkoBinaryDescription(
        key="service_agreement",
        translation_key="service_agreement",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda g: g.device.get("hasServiceAgreement"),
        exists_fn=lambda g: g.device.get("hasServiceAgreement") is not None,
    ),
    RehlkoBinaryDescription(
        key="cellular_kit_online",
        translation_key="cellular_kit_online",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda g: g.details.get("cellularKitOnline"),
        exists_fn=lambda g: g.details.get("cellularKitOnline") is not None,
    ),
    RehlkoBinaryDescription(
        key="wifi_connected",
        translation_key="wifi_connected",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda g: g.hub.get("wifiConnected"),
        exists_fn=lambda g: "wifiConnected" in g.hub,
    ),
    RehlkoBinaryDescription(
        key="cellular_connected",
        translation_key="cellular_connected",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda g: g.hub.get("cellularConnected"),
        exists_fn=lambda g: "cellularConnected" in g.hub,
    ),
    RehlkoBinaryDescription(
        key="load_module_connected",
        translation_key="load_module_connected",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda g: g.load_shed.get("isConnected"),
        exists_fn=lambda g: bool(g.load_shed),
    ),
    RehlkoBinaryDescription(
        key="pim_connected",
        translation_key="pim_connected",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda g: g.pim.get("isConnected"),
        exists_fn=lambda g: bool(g.pim),
    ),
    RehlkoBinaryDescription(
        key="firmware_update_available",
        translation_key="firmware_update_available",
        device_class=BinarySensorDeviceClass.UPDATE,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda g: g.firmware_update.get("canBeUpdated"),
        exists_fn=lambda g: bool(g.firmware_update),
    ),
)

HANDLED_BOOLS = {
    "isConnected",
    "engineOilPressureOk",
    "hasServiceAgreement",
    "cellularKitOnline",
    "autoFirmwareUpdateEnabled",
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: RehlkoConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    created: set[str] = set()

    @callback
    def _discover() -> None:
        new: list[BinarySensorEntity] = []
        for device_id, gen in coordinator.data.generators.items():
            for description in BINARY_SENSORS:
                uid = f"{device_id}-{description.key}"
                if uid in created or (description.exists_fn and not description.exists_fn(gen)):
                    continue
                created.add(uid)
                new.append(RehlkoBinarySensor(coordinator, device_id, description))
            if entry.options.get(CONF_EXTRA_DIAGNOSTICS, DEFAULT_EXTRA_DIAGNOSTICS):
                for source, payload in (("device", gen.device), ("details", gen.details)):
                    for key, value in payload.items():
                        if not isinstance(value, bool) or key in HANDLED_BOOLS:
                            continue
                        uid = f"{device_id}-extra-{key}"
                        if uid in created:
                            continue
                        created.add(uid)
                        new.append(ExtraFlagSensor(coordinator, device_id, source, key))
        if new:
            async_add_entities(new)

    _discover()
    entry.async_on_unload(coordinator.async_add_listener(_discover))


class RehlkoBinarySensor(RehlkoEntity, BinarySensorEntity):
    entity_description: RehlkoBinaryDescription

    def __init__(
        self, coordinator: RehlkoCoordinator, device_id: int, description: RehlkoBinaryDescription
    ) -> None:
        super().__init__(coordinator, device_id, description.key)
        self.entity_description = description

    @property
    def is_on(self) -> bool | None:
        value = value_or_none(self.entity_description.value_fn, self.gen)
        return None if value is None else bool(value)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        fn = self.entity_description.attrs_fn
        return value_or_none(fn, self.gen) if fn else None


class ExtraFlagSensor(RehlkoEntity, BinarySensorEntity):
    """A boolean field the API reports that no dedicated entity covers."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_translation_key = "extra_flag"
    _attr_entity_registry_enabled_default = False

    def __init__(
        self, coordinator: RehlkoCoordinator, device_id: int, source: str, key: str
    ) -> None:
        super().__init__(coordinator, device_id, f"extra-{key}")
        self._source = source
        self._key = key
        self._attr_translation_placeholders = {"field": humanize(key) or key}

    @property
    def is_on(self) -> bool | None:
        gen = self.gen
        if gen is None:
            return None
        value = (gen.device if self._source == "device" else gen.details).get(self._key)
        return None if value is None else bool(value)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {"api_field": self._key, "source": self._source}
