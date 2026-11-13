"""Sensors: telemetry, totals, states, timestamps, profile, diagnostics and energy."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from homeassistant.components.sensor import (
    RestoreSensor,
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
    REVOLUTIONS_PER_MINUTE,
    EntityCategory,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfFrequency,
    UnitOfInformation,
    UnitOfPower,
    UnitOfPressure,
    UnitOfTemperature,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util

from . import RehlkoConfigEntry
from .api import vocabulary as V
from .api.util import as_float, humanize, parse_timestamp, slugify
from .const import CONF_EXTRA_DIAGNOSTICS, DEFAULT_EXTRA_DIAGNOSTICS
from .coordinator import RehlkoCoordinator
from .entity import RehlkoEntity, ats_device_info, value_or_none
from .models import GeneratorData

PARALLEL_UPDATES = 0


def _site_tz():
    return dt_util.get_default_time_zone()


def _ts(value: Any) -> datetime | None:
    return parse_timestamp(value, _site_tz())


@dataclass(frozen=True, kw_only=True)
class RehlkoSensorDescription(SensorEntityDescription):
    value_fn: Callable[[GeneratorData], Any]
    exists_fn: Callable[[GeneratorData], bool] | None = None
    attrs_fn: Callable[[GeneratorData], dict[str, Any] | None] | None = None
    enum_values: tuple[str, ...] | None = None
    on_ats: bool = False
    # Fields this description covers, so the catch-all does not duplicate them.
    covers: tuple[str, ...] = ()


def _detail(key: str) -> Callable[[GeneratorData], Any]:
    return lambda g: g.details.get(key)


def _device(key: str) -> Callable[[GeneratorData], Any]:
    return lambda g: g.device.get(key)


def _has_detail(key: str) -> Callable[[GeneratorData], bool]:
    return lambda g: key in g.details


def _has_device(key: str) -> Callable[[GeneratorData], bool]:
    return lambda g: key in g.device


def _num(key: str, *, source: str = "details") -> Callable[[GeneratorData], float | None]:
    if source == "details":
        return lambda g: as_float(g.details.get(key))
    return lambda g: as_float(g.device.get(key))


def _alerts_attrs(g: GeneratorData) -> dict[str, Any]:
    return {
        "alerts": [
            {
                "name": a.get("name") or humanize(a.get("deviceEventId")),
                "code": a.get("deviceEventId"),
                "level": a.get("level"),
                "timestamp": a.get("timestamp"),
                "critical": a.get("isCriticalFault"),
            }
            for a in g.alerts[:20]
        ]
    }


def _latest(items: list[dict[str, Any]]) -> dict[str, Any] | None:
    return items[0] if items else None


def _dealer(g: GeneratorData) -> dict[str, Any] | None:
    orgs = g.device.get("dealerOrgs") or []
    return orgs[0] if orgs and isinstance(orgs[0], dict) else None


def _address_text(address: dict[str, Any] | None) -> str | None:
    if not address:
        return None
    parts = [
        address.get("address1"),
        address.get("address2"),
        address.get("city"),
        address.get("postalCode"),
        address.get("country"),
    ]
    text = ", ".join(str(p) for p in parts if p)
    return text or None


def _maintenance_left(g: GeneratorData) -> float | None:
    due = _ts(g.device.get("nextMaintenanceTimestamp"))
    if due is None:
        return None
    return round((due - dt_util.utcnow()).total_seconds() / 86400, 1)


T = SensorDeviceClass.TEMPERATURE
M = SensorStateClass.MEASUREMENT
DIAG = EntityCategory.DIAGNOSTIC

SENSORS: tuple[RehlkoSensorDescription, ...] = (
    # ---- power & load -------------------------------------------------------------
    RehlkoSensorDescription(
        key="utility_voltage",
        translation_key="utility_voltage",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=M,
        value_fn=_num("utilityVoltageV"),
        exists_fn=_has_detail("utilityVoltageV"),
        covers=("utilityVoltageV",),
    ),
    RehlkoSensorDescription(
        key="generator_voltage",
        translation_key="generator_voltage",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=M,
        value_fn=_num("generatorVoltageAvgV"),
        exists_fn=_has_detail("generatorVoltageAvgV"),
        covers=("generatorVoltageAvgV",),
    ),
    RehlkoSensorDescription(
        key="generator_load",
        translation_key="generator_load",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=M,
        value_fn=_num("generatorLoadW"),
        exists_fn=_has_detail("generatorLoadW"),
        covers=("generatorLoadW",),
    ),
    RehlkoSensorDescription(
        key="generator_load_percent",
        translation_key="generator_load_percent",
        native_unit_of_measurement=PERCENTAGE,
        state_class=M,
        value_fn=_num("generatorLoadPercent"),
        exists_fn=_has_detail("generatorLoadPercent"),
        covers=("generatorLoadPercent",),
    ),
    RehlkoSensorDescription(
        key="set_output_voltage",
        translation_key="set_output_voltage",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        entity_category=DIAG,
        value_fn=_num("setOutputVoltageV"),
        exists_fn=_has_detail("setOutputVoltageV"),
        covers=("setOutputVoltageV",),
    ),
    RehlkoSensorDescription(
        key="power_source",
        translation_key="power_source",
        device_class=SensorDeviceClass.ENUM,
        enum_values=V.POWER_SOURCE,
        value_fn=_detail("powerSource"),
        exists_fn=_has_detail("powerSource"),
        covers=("powerSource",),
    ),
    # ---- engine ---------------------------------------------------------------------
    RehlkoSensorDescription(
        key="engine_speed",
        translation_key="engine_speed",
        native_unit_of_measurement=REVOLUTIONS_PER_MINUTE,
        state_class=M,
        value_fn=_num("engineSpeedRpm"),
        exists_fn=_has_detail("engineSpeedRpm"),
        covers=("engineSpeedRpm",),
    ),
    RehlkoSensorDescription(
        key="engine_frequency",
        translation_key="engine_frequency",
        native_unit_of_measurement=UnitOfFrequency.HERTZ,
        device_class=SensorDeviceClass.FREQUENCY,
        state_class=M,
        value_fn=_num("engineFrequencyHz"),
        exists_fn=_has_detail("engineFrequencyHz"),
        covers=("engineFrequencyHz",),
    ),
    RehlkoSensorDescription(
        key="engine_oil_pressure",
        translation_key="engine_oil_pressure",
        native_unit_of_measurement=UnitOfPressure.PSI,
        device_class=SensorDeviceClass.PRESSURE,
        state_class=M,
        value_fn=_num("engineOilPressurePsi"),
        exists_fn=_has_detail("engineOilPressurePsi"),
        covers=("engineOilPressurePsi",),
    ),
    RehlkoSensorDescription(
        key="engine_coolant_temperature",
        translation_key="engine_coolant_temperature",
        native_unit_of_measurement=UnitOfTemperature.FAHRENHEIT,
        device_class=T,
        state_class=M,
        value_fn=_num("engineCoolantTempF"),
        exists_fn=_has_detail("engineCoolantTempF"),
        covers=("engineCoolantTempF",),
    ),
    RehlkoSensorDescription(
        key="lube_oil_temperature",
        translation_key="lube_oil_temperature",
        native_unit_of_measurement=UnitOfTemperature.FAHRENHEIT,
        device_class=T,
        state_class=M,
        value_fn=_num("lubeOilTempF"),
        exists_fn=_has_detail("lubeOilTempF"),
        covers=("lubeOilTempF",),
    ),
    RehlkoSensorDescription(
        key="engine_compartment_temperature",
        translation_key="engine_compartment_temperature",
        native_unit_of_measurement=UnitOfTemperature.FAHRENHEIT,
        device_class=T,
        state_class=M,
        value_fn=_num("engineCompartmentTempF"),
        exists_fn=_has_detail("engineCompartmentTempF"),
        covers=("engineCompartmentTempF",),
    ),
    RehlkoSensorDescription(
        key="engine_state",
        translation_key="engine_state",
        device_class=SensorDeviceClass.ENUM,
        enum_values=V.GENSET_STATE,
        value_fn=lambda g: g.engine_state,
        attrs_fn=lambda g: {"display_name": g.get("engineStateDisplayNameEn")},
        exists_fn=lambda g: "engineState" in g.details or "engineState" in g.device,
        covers=("engineState", "engineStateDisplayNameEn"),
    ),
    RehlkoSensorDescription(
        key="fuel_level",
        translation_key="fuel_level",
        native_unit_of_measurement=PERCENTAGE,
        state_class=M,
        value_fn=_num("fuelLevelPercent"),
        exists_fn=lambda g: g.details.get("fuelLevelPercent") is not None,
        covers=("fuelLevelPercent",),
    ),
    # ---- controller -----------------------------------------------------------------
    RehlkoSensorDescription(
        key="battery_voltage",
        translation_key="battery_voltage",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=M,
        suggested_display_precision=1,
        value_fn=_num("batteryVoltageV"),
        exists_fn=_has_detail("batteryVoltageV"),
        covers=("batteryVoltageV",),
    ),
    RehlkoSensorDescription(
        key="controller_temperature",
        translation_key="controller_temperature",
        native_unit_of_measurement=UnitOfTemperature.FAHRENHEIT,
        device_class=T,
        state_class=M,
        value_fn=_num("controllerTempF"),
        exists_fn=_has_detail("controllerTempF"),
        covers=("controllerTempF",),
    ),
    RehlkoSensorDescription(
        key="controller_clock",
        translation_key="controller_clock",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=DIAG,
        value_fn=lambda g: _ts(g.details.get("controllerClockTimestamp")),
        exists_fn=_has_detail("controllerClockTimestamp"),
        covers=("controllerClockTimestamp",),
    ),
    RehlkoSensorDescription(
        key="status",
        translation_key="status",
        device_class=SensorDeviceClass.ENUM,
        enum_values=V.DEVICE_STATUS,
        value_fn=lambda g: g.status,
        attrs_fn=lambda g: {
            "shutdown_reason": humanize(g.device.get("shutdownReason")),
            "status_updated": g.device.get("statusUpdateTimestamp"),
        },
        covers=("status",),
    ),
    RehlkoSensorDescription(
        key="switch_state",
        translation_key="switch_state",
        device_class=SensorDeviceClass.ENUM,
        enum_values=V.SWITCH_STATE,
        value_fn=_detail("switchState"),
        exists_fn=_has_detail("switchState"),
        covers=("switchState",),
    ),
    RehlkoSensorDescription(
        key="shutdown_reason",
        translation_key="shutdown_reason",
        value_fn=lambda g: humanize(g.device.get("shutdownReason")) or "None",
        attrs_fn=lambda g: {"code": g.device.get("shutdownReason")},
        exists_fn=_has_device("shutdownReason"),
        covers=("shutdownReason",),
    ),
    RehlkoSensorDescription(
        key="alert_count",
        translation_key="alert_count",
        state_class=M,
        value_fn=lambda g: (
            g.device.get("alertCount") if g.device.get("alertCount") is not None else len(g.alerts)
        ),
        attrs_fn=_alerts_attrs,
        covers=("alertCount",),
    ),
    # ---- runtime & maintenance ------------------------------------------------------
    RehlkoSensorDescription(
        key="total_runtime",
        translation_key="total_runtime",
        native_unit_of_measurement=UnitOfTime.HOURS,
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=1,
        value_fn=lambda g: as_float(g.get("totalRuntimeHours")),
        exists_fn=lambda g: g.get("totalRuntimeHours") is not None,
        covers=("totalRuntimeHours",),
    ),
    RehlkoSensorDescription(
        key="total_operation",
        translation_key="total_operation",
        native_unit_of_measurement=UnitOfTime.HOURS,
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.TOTAL_INCREASING,
        suggested_display_precision=1,
        value_fn=_num("totalOperationHours"),
        exists_fn=_has_detail("totalOperationHours"),
        covers=("totalOperationHours",),
    ),
    RehlkoSensorDescription(
        key="runtime_since_maintenance",
        translation_key="runtime_since_maintenance",
        native_unit_of_measurement=UnitOfTime.HOURS,
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.TOTAL,
        suggested_display_precision=1,
        value_fn=_num("runtimeSinceLastMaintenanceHours"),
        exists_fn=_has_detail("runtimeSinceLastMaintenanceHours"),
        covers=("runtimeSinceLastMaintenanceHours",),
    ),
    RehlkoSensorDescription(
        key="last_run",
        translation_key="last_run",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda g: _ts(g.details.get("lastRanTimestamp")),
        exists_fn=_has_detail("lastRanTimestamp"),
        covers=("lastRanTimestamp",),
    ),
    RehlkoSensorDescription(
        key="last_maintenance",
        translation_key="last_maintenance",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda g: _ts(g.device.get("lastMaintenanceTimestamp")),
        exists_fn=_has_device("lastMaintenanceTimestamp"),
        covers=("lastMaintenanceTimestamp",),
    ),
    RehlkoSensorDescription(
        key="next_maintenance",
        translation_key="next_maintenance",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda g: _ts(g.device.get("nextMaintenanceTimestamp")),
        attrs_fn=lambda g: {"days_remaining": _maintenance_left(g)},
        exists_fn=_has_device("nextMaintenanceTimestamp"),
        covers=("nextMaintenanceTimestamp",),
    ),
    RehlkoSensorDescription(
        key="maintenance_period",
        translation_key="maintenance_period",
        native_unit_of_measurement=UnitOfTime.DAYS,
        device_class=SensorDeviceClass.DURATION,
        entity_category=DIAG,
        value_fn=_num("maintenancePeriodDays", source="device"),
        exists_fn=_has_device("maintenancePeriodDays"),
        covers=("maintenancePeriodDays",),
    ),
    RehlkoSensorDescription(
        key="last_maintenance_note",
        translation_key="last_maintenance_note",
        value_fn=lambda g: (
            ((_latest(g.maintenance_notes) or {}).get("contents") or "")[:255] or None
        ),
        attrs_fn=lambda g: {
            "timestamp": (_latest(g.maintenance_notes) or {}).get("timestamp"),
            "by_dealer": (_latest(g.maintenance_notes) or {}).get("authorIsDealer"),
            "author": (_latest(g.maintenance_notes) or {}).get("dealerAuthor"),
            "notes": len(g.maintenance_notes),
        },
    ),
    # ---- exercise -------------------------------------------------------------------
    RehlkoSensorDescription(
        key="next_exercise",
        translation_key="next_exercise",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda g: _ts(g.exercise.get("nextStartTimestamp")),
        attrs_fn=lambda g: {
            "mode": g.exercise.get("mode"),
            "frequency": g.exercise.get("frequency"),
            "duration_minutes": g.exercise.get("durationMinutes"),
        },
        exists_fn=lambda g: "exercise" in g.details,
    ),
    RehlkoSensorDescription(
        key="last_exercise_start",
        translation_key="last_exercise_start",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda g: _ts(g.exercise.get("lastStartTimestamp")),
        exists_fn=lambda g: "exercise" in g.details,
    ),
    RehlkoSensorDescription(
        key="last_exercise_end",
        translation_key="last_exercise_end",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda g: _ts(g.exercise.get("lastEndTimestamp")),
        exists_fn=lambda g: "exercise" in g.details,
    ),
    RehlkoSensorDescription(
        key="exercise_running_mode",
        translation_key="exercise_running_mode",
        device_class=SensorDeviceClass.ENUM,
        enum_values=V.EXERCISE_MODE,
        value_fn=lambda g: g.exercise.get("runningMode") or "None",
        exists_fn=lambda g: "exercise" in g.details,
    ),
    # ---- activity -------------------------------------------------------------------
    RehlkoSensorDescription(
        key="last_event",
        translation_key="last_event",
        value_fn=lambda g: (
            (_latest(g.events) or {}).get("name")
            or humanize((_latest(g.events) or {}).get("deviceEventId"))
        ),
        attrs_fn=lambda g: {
            "code": (_latest(g.events) or {}).get("deviceEventId"),
            "level": (_latest(g.events) or {}).get("level"),
            "timestamp": (_latest(g.events) or {}).get("timestamp"),
        },
    ),
    RehlkoSensorDescription(
        key="last_notification",
        translation_key="last_notification",
        value_fn=lambda g: ((_latest(g.notifications) or {}).get("message") or "")[:255] or None,
        attrs_fn=lambda g: {
            "type": (_latest(g.notifications) or {}).get("type"),
            "timestamp": (_latest(g.notifications) or {}).get("timestamp"),
        },
    ),
    # ---- site -----------------------------------------------------------------------
    RehlkoSensorDescription(
        key="weather_temperature",
        translation_key="weather_temperature",
        native_unit_of_measurement=UnitOfTemperature.FAHRENHEIT,
        device_class=T,
        state_class=M,
        value_fn=lambda g: as_float(g.home.get("weatherTempF")),
        exists_fn=lambda g: "weatherTempF" in g.home,
    ),
    RehlkoSensorDescription(
        key="weather_condition",
        translation_key="weather_condition",
        device_class=SensorDeviceClass.ENUM,
        enum_values=V.WEATHER_CONDITION,
        value_fn=lambda g: g.home.get("weatherCondition"),
        attrs_fn=lambda g: {"time_period": g.home.get("weatherTimePeriod")},
        exists_fn=lambda g: "weatherCondition" in g.home,
    ),
    # ---- profile (diagnostic) -------------------------------------------------------
    RehlkoSensorDescription(
        key="model",
        translation_key="model",
        entity_category=DIAG,
        value_fn=lambda g: g.device.get("modelDisplayName") or humanize(g.device.get("model")),
        attrs_fn=lambda g: {"code": g.device.get("model")},
        covers=("model", "modelDisplayName"),
    ),
    RehlkoSensorDescription(
        key="product",
        translation_key="product",
        entity_category=DIAG,
        value_fn=lambda g: g.device.get("productDisplayName") or humanize(g.device.get("product")),
        attrs_fn=lambda g: {"code": g.device.get("product")},
        covers=("product", "productDisplayName"),
    ),
    RehlkoSensorDescription(
        key="controller_type",
        translation_key="controller_type",
        entity_category=DIAG,
        value_fn=_device("controllerType"),
        exists_fn=_has_device("controllerType"),
        covers=("controllerType",),
    ),
    RehlkoSensorDescription(
        key="firmware_version",
        translation_key="firmware_version",
        entity_category=DIAG,
        value_fn=lambda g: g.device.get("firmwareVersion"),
        exists_fn=_has_device("firmwareVersion"),
        covers=("firmwareVersion",),
    ),
    RehlkoSensorDescription(
        key="current_firmware",
        translation_key="current_firmware",
        entity_category=DIAG,
        value_fn=_device("currentFirmware"),
        exists_fn=_has_device("currentFirmware"),
        covers=("currentFirmware",),
    ),
    RehlkoSensorDescription(
        key="fuel_type",
        translation_key="fuel_type",
        device_class=SensorDeviceClass.ENUM,
        enum_values=V.FUEL_TYPE,
        entity_category=DIAG,
        value_fn=_detail("fuelType"),
        exists_fn=_has_detail("fuelType"),
        covers=("fuelType",),
    ),
    RehlkoSensorDescription(
        key="cooling_type",
        translation_key="cooling_type",
        device_class=SensorDeviceClass.ENUM,
        enum_values=V.COOLING_TYPE,
        entity_category=DIAG,
        value_fn=_detail("coolingType"),
        exists_fn=_has_detail("coolingType"),
        covers=("coolingType",),
    ),
    RehlkoSensorDescription(
        key="connection_type",
        translation_key="connection_type",
        device_class=SensorDeviceClass.ENUM,
        enum_values=V.CONNECTION_TYPE,
        entity_category=DIAG,
        value_fn=lambda g: g.get("connectionType"),
        covers=("connectionType",),
    ),
    RehlkoSensorDescription(
        key="device_ip_address",
        translation_key="device_ip_address",
        entity_category=DIAG,
        entity_registry_enabled_default=False,
        value_fn=_device("deviceIpAddress"),
        exists_fn=_has_device("deviceIpAddress"),
        covers=("deviceIpAddress",),
    ),
    RehlkoSensorDescription(
        key="server_ip_address",
        translation_key="server_ip_address",
        entity_category=DIAG,
        entity_registry_enabled_default=False,
        value_fn=_detail("serverIpAddress"),
        exists_fn=_has_detail("serverIpAddress"),
        covers=("serverIpAddress",),
    ),
    RehlkoSensorDescription(
        key="mac_address",
        translation_key="mac_address",
        entity_category=DIAG,
        entity_registry_enabled_default=False,
        value_fn=_device("macAddress"),
        exists_fn=_has_device("macAddress"),
        covers=("macAddress",),
    ),
    RehlkoSensorDescription(
        key="last_connected",
        translation_key="last_connected",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=DIAG,
        value_fn=lambda g: _ts(g.device.get("lastConnectedTimestamp")),
        exists_fn=_has_device("lastConnectedTimestamp"),
        covers=("lastConnectedTimestamp",),
    ),
    RehlkoSensorDescription(
        key="status_updated",
        translation_key="status_updated",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=DIAG,
        value_fn=lambda g: _ts(g.device.get("statusUpdateTimestamp")),
        exists_fn=_has_device("statusUpdateTimestamp"),
        covers=("statusUpdateTimestamp",),
    ),
    RehlkoSensorDescription(
        key="parameters_updated",
        translation_key="parameters_updated",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=DIAG,
        value_fn=lambda g: _ts(g.device.get("latestParameterUpdateTimestamp")),
        exists_fn=_has_device("latestParameterUpdateTimestamp"),
        covers=("latestParameterUpdateTimestamp",),
    ),
    RehlkoSensorDescription(
        key="uptime_percent",
        translation_key="uptime_percent",
        native_unit_of_measurement=PERCENTAGE,
        state_class=M,
        entity_category=DIAG,
        value_fn=_num("uptimePercent", source="device"),
        exists_fn=_has_device("uptimePercent"),
        covers=("uptimePercent",),
    ),
    RehlkoSensorDescription(
        key="remote_reset_counter",
        translation_key="remote_reset_counter",
        native_unit_of_measurement=UnitOfTime.SECONDS,
        device_class=SensorDeviceClass.DURATION,
        entity_category=DIAG,
        value_fn=_num("remoteResetCounterSeconds"),
        exists_fn=_has_detail("remoteResetCounterSeconds"),
        covers=("remoteResetCounterSeconds",),
    ),
    RehlkoSensorDescription(
        key="wifi_strength",
        translation_key="wifi_strength",
        device_class=SensorDeviceClass.ENUM,
        enum_values=V.SIGNAL_STRENGTH,
        entity_category=DIAG,
        value_fn=lambda g: g.hub.get("wifiStrength"),
        exists_fn=lambda g: "wifiStrength" in g.hub,
    ),
    RehlkoSensorDescription(
        key="cellular_strength",
        translation_key="cellular_strength",
        device_class=SensorDeviceClass.ENUM,
        enum_values=V.SIGNAL_STRENGTH,
        entity_category=DIAG,
        value_fn=lambda g: g.hub.get("cellularStrength"),
        exists_fn=lambda g: "cellularStrength" in g.hub,
    ),
    RehlkoSensorDescription(
        key="site_address",
        translation_key="site_address",
        entity_category=DIAG,
        entity_registry_enabled_default=False,
        value_fn=lambda g: _address_text(g.device.get("address") or g.home.get("address")),
        covers=("address",),
    ),
    RehlkoSensorDescription(
        key="dealer",
        translation_key="dealer",
        entity_category=DIAG,
        value_fn=lambda g: (_dealer(g) or {}).get("name"),
        attrs_fn=lambda g: (
            {k: (_dealer(g) or {}).get(k) for k in ("displayPhoneNumber", "businessPartnerNo")}
            | {"address": _address_text((_dealer(g) or {}).get("address"))}
        ),
        exists_fn=lambda g: _dealer(g) is not None,
        covers=("dealerOrgs",),
    ),
    # ---- service agreement & cellular (diagnostic) ----------------------------------
    RehlkoSensorDescription(
        key="service_agreement_status",
        translation_key="service_agreement_status",
        device_class=SensorDeviceClass.ENUM,
        enum_values=V.SERVICE_AGREEMENT_STATUS,
        entity_category=DIAG,
        value_fn=_device("serviceAgreementStatus"),
        attrs_fn=lambda g: {
            "term": g.service_agreement.get("term"),
            "term_months": g.service_agreement.get("termMonths"),
            "term_days": g.service_agreement.get("termDays"),
            "begins": g.service_agreement.get("beginTimestamp"),
        },
        exists_fn=_has_device("serviceAgreementStatus"),
        covers=("serviceAgreementStatus",),
    ),
    RehlkoSensorDescription(
        key="cellular_data_status",
        translation_key="cellular_data_status",
        device_class=SensorDeviceClass.ENUM,
        enum_values=V.CELLULAR_DATA_STATUS,
        entity_category=DIAG,
        value_fn=lambda g: g.get("cellularDataStatus"),
        exists_fn=lambda g: g.get("cellularDataStatus") is not None,
        covers=("cellularDataStatus",),
    ),
    RehlkoSensorDescription(
        key="cellular_data_used",
        translation_key="cellular_data_used",
        native_unit_of_measurement=PERCENTAGE,
        state_class=M,
        entity_category=DIAG,
        value_fn=lambda g: as_float(g.get("cellularDataPercentage")),
        exists_fn=lambda g: g.get("cellularDataPercentage") is not None,
        covers=("cellularDataPercentage",),
    ),
    RehlkoSensorDescription(
        key="cellular_expiry",
        translation_key="cellular_expiry",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=DIAG,
        value_fn=lambda g: _ts(g.get("cellularExpiryDate")),
        exists_fn=lambda g: g.get("cellularExpiryDate") is not None,
        covers=("cellularExpiryDate",),
    ),
    RehlkoSensorDescription(
        key="cellular_installed",
        translation_key="cellular_installed",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=DIAG,
        value_fn=lambda g: _ts(g.details.get("cellularInstallationDate")),
        exists_fn=lambda g: g.details.get("cellularInstallationDate") is not None,
        covers=("cellularInstallationDate",),
    ),
    RehlkoSensorDescription(
        key="cell_kit_payment_status",
        translation_key="cell_kit_payment_status",
        device_class=SensorDeviceClass.ENUM,
        enum_values=V.CELL_KIT_PAYMENT_STATUS,
        entity_category=DIAG,
        value_fn=_device("cellKitPaymentStatus"),
        exists_fn=lambda g: g.device.get("cellKitPaymentStatus") is not None,
        covers=("cellKitPaymentStatus",),
    ),
    RehlkoSensorDescription(
        key="cell_data_remaining",
        translation_key="cell_data_remaining",
        native_unit_of_measurement=UnitOfInformation.MEGABYTES,
        device_class=SensorDeviceClass.DATA_SIZE,
        state_class=M,
        entity_category=DIAG,
        value_fn=lambda g: as_float((g.cell_plan or {}).get("remainingDataMb")),
        attrs_fn=lambda g: {
            "total_mb": (g.cell_plan or {}).get("totalDataMb"),
            "expires": (g.cell_plan or {}).get("expiryDate"),
        },
        exists_fn=lambda g: bool(g.cell_plan),
    ),
    RehlkoSensorDescription(
        key="scheduled_firmware_update",
        translation_key="scheduled_firmware_update",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=DIAG,
        value_fn=lambda g: _ts(g.details.get("scheduledFirmwareUpdateTimestamp")),
        exists_fn=_has_detail("scheduledFirmwareUpdateTimestamp"),
        covers=("scheduledFirmwareUpdateTimestamp",),
    ),
    RehlkoSensorDescription(
        key="install_progress",
        translation_key="install_progress",
        entity_category=DIAG,
        entity_registry_enabled_default=False,
        value_fn=lambda g: humanize(g.install_progress.get("type")),
        attrs_fn=lambda g: {
            "completed_steps": g.install_progress.get("completedSteps"),
            "modified": g.install_progress.get("modifiedDate"),
        },
        exists_fn=lambda g: bool(g.install_progress),
    ),
    # ---- transfer switch (own device) -----------------------------------------------
    RehlkoSensorDescription(
        key="ats_power_source",
        translation_key="ats_power_source",
        device_class=SensorDeviceClass.ENUM,
        enum_values=V.POWER_SOURCE,
        on_ats=True,
        value_fn=lambda g: g.ats.get("powerSource"),
        exists_fn=lambda g: "powerSource" in g.ats,
    ),
    RehlkoSensorDescription(
        key="ats_connection_type",
        translation_key="ats_connection_type",
        device_class=SensorDeviceClass.ENUM,
        enum_values=V.SUB_DEVICE_CONNECTION_TYPE,
        entity_category=DIAG,
        on_ats=True,
        value_fn=lambda g: g.ats.get("atsConnectionType"),
        exists_fn=lambda g: "atsConnectionType" in g.ats,
    ),
    RehlkoSensorDescription(
        key="ats_signal_strength",
        translation_key="ats_signal_strength",
        device_class=SensorDeviceClass.ENUM,
        enum_values=V.SIGNAL_STRENGTH,
        entity_category=DIAG,
        on_ats=True,
        value_fn=lambda g: g.ats.get("ismSignalStrength"),
        exists_fn=lambda g: "ismSignalStrength" in g.ats,
    ),
)

# Keys the descriptions above (or other platforms) already expose; the catch-all skips them.
HANDLED_KEYS = {key for d in SENSORS for key in d.covers} | {
    # structures handled elsewhere or not meaningful as a single value
    "id",
    "device",
    "generators",
    "exercise",
    "loadShed",
    "pim",
    "ats",
    "installProgress",
    "firmwareUpdate",
    "serviceAgreement",
    "addedBy",
    "associatedUsers",
    "hubData",
    "dealerOrgs",
    "address",
    "serialNumber",
    "displayName",
    "deviceHost",
    # booleans exposed by binary_sensor / switch
    "isConnected",
    "engineOilPressureOk",
    "hasServiceAgreement",
    "cellularKitOnline",
    "autoFirmwareUpdateEnabled",
    "hasAcceptedPrivacyPolicy",
}


def _slug_options(values: tuple[str, ...]) -> list[str]:
    seen: list[str] = []
    for value in values:
        slug = slugify(value)
        if slug and slug not in seen:
            seen.append(slug)
    return seen


async def async_setup_entry(
    hass: HomeAssistant,
    entry: RehlkoConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    created: set[str] = set()

    @callback
    def _discover() -> None:
        new: list[SensorEntity] = []
        for device_id, gen in coordinator.data.generators.items():
            for description in SENSORS:
                uid = f"{device_id}-{description.key}"
                if uid in created:
                    continue
                if description.on_ats and ats_device_info(gen) is None:
                    continue
                if description.exists_fn is not None and not description.exists_fn(gen):
                    continue
                created.add(uid)
                new.append(RehlkoSensor(coordinator, device_id, description))
            uid = f"{device_id}-energy_produced"
            if uid not in created and "generatorLoadW" in gen.details:
                created.add(uid)
                new.append(EnergyProducedSensor(coordinator, device_id))
            for kind, param in gen.peripheral_parameters():
                uid = f"{device_id}-peripheral-{param['definitionId']}"
                if uid not in created:
                    created.add(uid)
                    new.append(
                        PeripheralSensor(coordinator, device_id, kind, param["definitionId"])
                    )
            if entry.options.get(CONF_EXTRA_DIAGNOSTICS, DEFAULT_EXTRA_DIAGNOSTICS):
                for source, payload in (("device", gen.device), ("details", gen.details)):
                    for key, value in payload.items():
                        if key in HANDLED_KEYS or isinstance(value, (bool, dict, list)):
                            continue
                        uid = f"{device_id}-extra-{key}"
                        if uid in created:
                            continue
                        created.add(uid)
                        new.append(ExtraFieldSensor(coordinator, device_id, source, key))
        if new:
            async_add_entities(new)

    _discover()
    entry.async_on_unload(coordinator.async_add_listener(_discover))


class RehlkoSensor(RehlkoEntity, SensorEntity):
    entity_description: RehlkoSensorDescription

    def __init__(
        self, coordinator: RehlkoCoordinator, device_id: int, description: RehlkoSensorDescription
    ) -> None:
        gen = coordinator.data.generators[device_id]
        super().__init__(
            coordinator,
            device_id,
            description.key,
            device_info=ats_device_info(gen) if description.on_ats else None,
        )
        self.entity_description = description
        if description.enum_values is not None:
            self._base_options = _slug_options(description.enum_values)

    @property
    def device_info(self) -> DeviceInfo | None:
        # Read when Home Assistant registers the entity: only then can the transfer switch be
        # linked to its generator's device, which has to be in the device registry first.
        gen = self.gen
        if self.entity_description.on_ats and gen is not None and self.hass is not None:
            return ats_device_info(gen, self.coordinator)
        return self._attr_device_info

    @property
    def native_value(self) -> Any:
        value = value_or_none(self.entity_description.value_fn, self.gen)
        if self.entity_description.enum_values is not None:
            return slugify(value) if value not in (None, "") else None
        return value

    @property
    def options(self) -> list[str] | None:
        if self.entity_description.enum_values is None:
            return None
        current = self.native_value
        if current is not None and current not in self._base_options:
            return [*self._base_options, current]  # a value newer than this integration
        return self._base_options

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        fn = self.entity_description.attrs_fn
        return value_or_none(fn, self.gen) if fn else None


class EnergyProducedSensor(RehlkoEntity, RestoreSensor):
    """Energy the generator has delivered, for the Energy dashboard and long-term statistics.

    The service reports power (`generatorLoadW`), not energy, so this adds it up between polls
    with the trapezoidal rule and keeps the total across restarts. It is an estimate: a load
    that changes between two polls is seen only at its ends, and nothing is counted while Home
    Assistant is stopped or the generator's readings are unavailable.
    """

    _attr_translation_key = "energy_produced"
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
    _attr_suggested_display_precision = 2

    def __init__(self, coordinator: RehlkoCoordinator, device_id: int) -> None:
        super().__init__(coordinator, device_id, "energy_produced")
        self._total = 0.0
        self._sample: tuple[datetime, float] | None = None  # when, and watts then

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last = await self.async_get_last_sensor_data()
        restored = as_float(last.native_value) if last else None
        if restored is not None and restored >= 0:
            self._total = restored
        self._integrate()

    @callback
    def _handle_coordinator_update(self) -> None:
        self._integrate()
        super()._handle_coordinator_update()

    def _integrate(self) -> None:
        gen = self.gen
        watts = as_float(gen.details.get("generatorLoadW")) if gen else None
        if gen is None or not gen.details_available or gen.details_updated is None or watts is None:
            self._sample = None  # a gap in the readings is not bridged
            return
        watts = max(watts, 0.0) if gen.is_running else 0.0
        when = gen.details_updated
        if self._sample is not None:
            then, before = self._sample
            seconds = (when - then).total_seconds()
            # Twice the slowest poll, so a missed poll is tolerated but a suspended host is not.
            if 0 < seconds <= 2 * self.coordinator.longest_interval.total_seconds():
                self._total += (before + watts) / 2 * seconds / 3_600_000
            elif seconds <= 0:
                return  # the same reading again
        self._sample = (when, watts)

    @property
    def native_value(self) -> float:
        return round(self._total, 4)


class PeripheralSensor(RehlkoEntity, SensorEntity):
    """One load-module or PIM parameter, as the service reports it."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self, coordinator: RehlkoCoordinator, device_id: int, kind: str, definition_id: Any
    ) -> None:
        super().__init__(coordinator, device_id, f"peripheral-{definition_id}")
        self._kind = kind
        self._definition_id = definition_id
        self._attr_translation_key = (
            "load_module_parameter" if kind == "loadShed" else "pim_parameter"
        )
        self._attr_translation_placeholders = {"name": self._label()}

    def _param(self) -> dict[str, Any] | None:
        gen = self.gen
        if gen is None:
            return None
        for kind, param in gen.peripheral_parameters():
            if kind == self._kind and str(param.get("definitionId")) == str(self._definition_id):
                return param
        return None

    def _label(self) -> str:
        param = self._param() or {}
        return str(param.get("displayName") or f"#{self._definition_id}")

    @property
    def available(self) -> bool:
        return super().available and self._param() is not None

    @property
    def native_value(self) -> Any:
        value = (self._param() or {}).get("value")
        if isinstance(value, bool):
            return "on" if value else "off"
        if isinstance(value, (dict, list)):
            return str(value)[:255]
        return value

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        param = self._param() or {}
        block = (
            (self.gen.load_shed if self._kind == "loadShed" else self.gen.pim) if self.gen else {}
        )
        return {
            "definition_id": self._definition_id,
            "display_name": param.get("displayName"),
            "read_only": param.get("isReadOnly"),
            "peripheral": self._kind,
            "peripheral_connected": block.get("isConnected"),
        }


class ExtraFieldSensor(RehlkoEntity, SensorEntity):
    """A field the API reports that no dedicated entity covers (kept so nothing is lost)."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_translation_key = "extra_field"
    # Listed on the device page, one click from enabled, but not recorded until someone wants it.
    _attr_entity_registry_enabled_default = False

    def __init__(
        self, coordinator: RehlkoCoordinator, device_id: int, source: str, key: str
    ) -> None:
        super().__init__(coordinator, device_id, f"extra-{key}")
        self._source = source
        self._key = key
        self._attr_translation_placeholders = {"field": humanize(key) or key}

    @property
    def native_value(self) -> Any:
        gen = self.gen
        if gen is None:
            return None
        value = (gen.device if self._source == "device" else gen.details).get(self._key)
        if isinstance(value, str):
            ts = parse_timestamp(value) if value[:4].isdigit() and "T" in value else None
            return ts.isoformat() if ts else value[:255]
        return value

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {"api_field": self._key, "source": self._source}
