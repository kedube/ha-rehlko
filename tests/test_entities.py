"""Construct every sensor and binary-sensor against a rich sample generator.

This exercises each entity description's value/exists/attrs lambdas without a running Home
Assistant — the kind of extraction bug that a manifest/HACS check never catches.
"""

from __future__ import annotations

import copy
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any

import pytest

from custom_components.rehlko_energy import binary_sensor as bs
from custom_components.rehlko_energy import sensor as sensor_mod
from custom_components.rehlko_energy.entity import ats_device_info
from custom_components.rehlko_energy.models import AccountData, GeneratorData

SAMPLE_DEVICE: dict[str, Any] = {
    "id": 1,
    "serialNumber": "SN123",
    "displayName": "Home Generator",
    "deviceHost": "Hub",
    "status": "Running",
    "model": "Model24RCL",
    "modelDisplayName": "24RCL",
    "product": "Rdc2",
    "productDisplayName": "RDC2",
    "controllerType": "RDC2",
    "firmwareVersion": "3.14",
    "currentFirmware": "3.14.2",
    "isConnected": True,
    "connectionType": "KohlerWifi",
    "deviceIpAddress": "[::ffff:10.0.0.5]:42636",  # as reported: the socket, not the address
    "macAddress": "aa:bb:cc:dd:ee:ff",
    "lastConnectedTimestamp": "2026-11-12T20:00:00Z",
    "statusUpdateTimestamp": "2026-11-12T20:01:00Z",
    "latestParameterUpdateTimestamp": "2026-11-12T19:00:00Z",
    "shutdownReason": "None",
    "alertCount": 1,
    "lastMaintenanceTimestamp": "2026-05-01T10:00:00Z",
    "nextMaintenanceTimestamp": "2027-05-01T10:00:00Z",
    "maintenancePeriodDays": 365,
    "hasServiceAgreement": True,
    "serviceAgreementStatus": "Active",
    "totalRuntimeHours": 182.4,
    "uptimePercent": 99,
    "cellKitPaymentStatus": "Paid",
    "address": {"address1": "1 Example Way", "city": "Town", "postalCode": "00000"},
    "dealerOrgs": [
        {
            "name": "Example Power",
            "displayPhoneNumber": "(555) 010-0000",
            "businessPartnerNo": "BP1",
        }
    ],
    "hubData": {
        "wifiConnected": True,
        "wifiStrength": "Strong",
        "cellularConnected": False,
        "cellularStrength": "Weak",
    },
}
SAMPLE_DETAILS: dict[str, Any] = {
    "powerSource": "Generator",
    "switchState": "Auto",
    "coolingType": "Air",
    "connectionType": "KohlerWifi",
    "serverIpAddress": "203.0.113.7",
    "fuelType": "NaturalGas",
    "fuelLevelPercent": 80,
    "batteryVoltageV": 13.6,
    "engineCoolantTempF": 172,
    "engineFrequencyHz": 60.0,
    "engineSpeedRpm": 1800,
    "lubeOilTempF": 190,
    "controllerTempF": 95,
    "engineCompartmentTempF": 110,
    "engineOilPressurePsi": 48,
    "engineOilPressureOk": True,
    "generatorLoadW": 5400,
    "generatorLoadPercent": 23,
    "generatorVoltageAvgV": 241,
    "setOutputVoltageV": 240,
    "utilityVoltageV": 0,
    "engineState": "Running",
    "engineStateDisplayNameEn": "Running",
    "totalRuntimeHours": 182.4,
    "totalOperationHours": 190.1,
    "runtimeSinceLastMaintenanceHours": 12.5,
    "remoteResetCounterSeconds": 0,
    "lastRanTimestamp": "2026-11-12T19:30:00Z",
    "controllerClockTimestamp": "2026-11-12T20:05:00",
    "autoFirmwareUpdateEnabled": True,
    "scheduledFirmwareUpdateTimestamp": "2026-12-01T03:00:00Z",
    "cellularExpiryDate": "2027-01-01T00:00:00Z",
    "cellularInstallationDate": "2026-01-01T00:00:00Z",
    "cellularDataPercentage": 42,
    "cellularDataStatus": "Active",
    "cellularKitOnline": True,
    "exercise": {
        "frequency": "EveryOtherWeek",
        "mode": "Unloaded",
        "runningMode": "None",
        "durationMinutes": 20,
        "nextStartTimestamp": "2026-11-22T14:00:00",
        "lastStartTimestamp": "2026-11-08T14:00:00",
        "lastEndTimestamp": "2026-11-08T14:20:00",
        "supportsNextExerciseDateTimeParam": True,
    },
    "loadShed": {
        "isConnected": True,
        "parameters": [
            {"definitionId": 1, "displayName": "AC", "value": "On", "isReadOnly": False}
        ],
    },
    "pim": {
        "isConnected": True,
        "parameters": [
            {"definitionId": 2, "displayName": "Pump", "value": True, "isReadOnly": False}
        ],
    },
    "ats": {
        "serialNumber": "ATS1",
        "modelNo": "RXT",
        "powerSource": "Generator",
        "atsConnectionType": "Hardwired",
        "ismSignalStrength": "Strong",
    },
    "serviceAgreement": {
        "term": "Annual",
        "termMonths": 12,
        "termDays": 365,
        "beginTimestamp": "2026-01-01T00:00:00Z",
    },
    "firmwareUpdate": {
        "canBeUpdated": True,
        "versionName": "3.15",
        "releaseDate": "2026-11-01T00:00:00Z",
    },
    "installProgress": {
        "type": "Commissioned",
        "completedSteps": 8,
        "modifiedDate": "2026-01-01T00:00:00Z",
    },
    "generators": [{"serialNumber": "GEN1"}],
}


class FakeCoordinator:
    def __init__(self, gen: GeneratorData) -> None:
        self.data = AccountData(generators={gen.device_id: gen})
        self.config_entry = SimpleNamespace(entry_id="e1", title="acct")
        self.last_update_success = True
        self.longest_interval = timedelta(seconds=60)

    # CoordinatorEntity touches these during __init__/updates.
    @property
    def hass(self):
        return None

    def async_add_listener(self, *_a, **_k):
        return lambda: None


def build_sample_gen() -> GeneratorData:
    """A richly-populated generator (deep-copied so tests can mutate it freely)."""
    g = GeneratorData(
        device_id=1,
        home={
            "name": "Home",
            "weatherTempF": 41,
            "weatherCondition": "BrokenClouds",
            "weatherTimePeriod": "Day",
        },
        device=copy.deepcopy(SAMPLE_DEVICE),
        details=copy.deepcopy(SAMPLE_DETAILS),
    )
    g.alerts = [
        {
            "id": 9,
            "name": "High Oil Temp",
            "deviceEventId": "HighOilTempWarning",
            "level": "Warning",
            "timestamp": "2026-11-12T19:00:00Z",
            "isCriticalFault": False,
        }
    ]
    g.cell_plan = {"remainingDataMb": 300, "totalDataMb": 500, "expiryDate": "2027-01-01T00:00:00Z"}
    g.maintenance_notes = [
        {
            "id": 1,
            "timestamp": "2026-05-01T10:00:00Z",
            "contents": "Annual service",
            "authorIsDealer": True,
            "dealerAuthor": "Example Power",
        }
    ]
    g.events = [
        {
            "id": 1,
            "name": "Engine Started",
            "deviceEventId": "EngineStarted",
            "level": "Status",
            "timestamp": "2026-11-12T19:30:00Z",
            "type": "runningNotice",
        }
    ]
    g.notifications = [
        {
            "id": 1,
            "type": "EngineStartedNotice",
            "message": "started",
            "timestamp": "2026-11-12T19:30:00Z",
        }
    ]
    return g


@pytest.fixture
def sample_gen() -> GeneratorData:
    return build_sample_gen()


def test_every_sensor_builds_and_yields_a_value(sample_gen: GeneratorData) -> None:
    coord = FakeCoordinator(sample_gen)
    built = 0
    for desc in sensor_mod.SENSORS:
        if desc.on_ats and ats_device_info(sample_gen) is None:
            continue
        if desc.exists_fn is not None and not desc.exists_fn(sample_gen):
            continue
        entity = sensor_mod.RehlkoSensor(coord, 1, desc)
        # native_value must not raise, and enum sensors must return a slug or None.
        value = entity.native_value
        if desc.enum_values is not None and value is not None:
            assert value in (entity.options or [])
        # attrs must not raise either.
        _ = entity.extra_state_attributes
        built += 1
    assert built > 40  # the sample exercises most descriptions


def test_key_sensor_values(sample_gen: GeneratorData) -> None:
    coord = FakeCoordinator(sample_gen)
    by_key = {d.key: d for d in sensor_mod.SENSORS}

    def value(key: str):
        return sensor_mod.RehlkoSensor(coord, 1, by_key[key]).native_value

    assert value("battery_voltage") == 13.6
    assert value("generator_load") == 5400
    assert value("engine_state") == "running"  # enum -> slug
    assert value("status") == "running"
    assert value("total_runtime") == 182.4
    assert value("power_source") == "generator"
    # The address alone, whichever way the service wraps it.
    assert value("device_ip_address") == "10.0.0.5"
    assert value("server_ip_address") == "203.0.113.7"
    sample_gen.details["serverIpAddress"] = "[::ffff:203.0.113.7]:443"
    assert value("server_ip_address") == "203.0.113.7"


def test_enum_sensor_passes_through_unknown_value(sample_gen: GeneratorData) -> None:
    sample_gen.device["status"] = "SomeFutureStatus"
    coord = FakeCoordinator(sample_gen)
    desc = next(d for d in sensor_mod.SENSORS if d.key == "status")
    entity = sensor_mod.RehlkoSensor(coord, 1, desc)
    assert entity.native_value == "some_future_status"
    assert "some_future_status" in entity.options  # added beyond the known options


def test_peripheral_and_extra_sensors_present(sample_gen: GeneratorData) -> None:
    coord = FakeCoordinator(sample_gen)
    per = sensor_mod.PeripheralSensor(coord, 1, "loadShed", 1)
    assert per.native_value == "On"
    assert per.extra_state_attributes["definition_id"] == 1
    extra = sensor_mod.ExtraFieldSensor(coord, 1, "details", "serverIpAddress")
    assert extra.native_value == "203.0.113.7"


def test_every_binary_sensor_builds(sample_gen: GeneratorData) -> None:
    coord = FakeCoordinator(sample_gen)
    results = {}
    for desc in bs.BINARY_SENSORS:
        if desc.exists_fn is not None and not desc.exists_fn(sample_gen):
            continue
        entity = bs.RehlkoBinarySensor(coord, 1, desc)
        results[desc.key] = entity.is_on
        _ = entity.extra_state_attributes
    assert results["running"] is True
    assert results["utility_power"] is False  # utility voltage 0
    assert results["on_generator_power"] is True
    assert results["not_in_auto"] is False  # switchState Auto
    assert results["oil_pressure_problem"] is False
    assert results["active_alerts"] is True


def test_binary_sensor_handles_missing_data() -> None:
    bare = GeneratorData(
        device_id=1, home={}, device={"status": "Offline", "isConnected": False}, details={}
    )
    coord = FakeCoordinator(bare)
    desc = next(d for d in bs.BINARY_SENSORS if d.key == "connected")
    assert bs.RehlkoBinarySensor(coord, 1, desc).is_on is False
    desc = next(d for d in bs.BINARY_SENSORS if d.key == "utility_power")
    assert bs.RehlkoBinarySensor(coord, 1, desc).is_on is None  # unknown, not False


def test_signal_strengths_are_translatable_enums(sample_gen: GeneratorData) -> None:
    coord = FakeCoordinator(sample_gen)
    by_key = {d.key: d for d in sensor_mod.SENSORS}
    for key, expected in (
        ("wifi_strength", "strong"),
        ("cellular_strength", "weak"),
        ("ats_signal_strength", "strong"),
    ):
        entity = sensor_mod.RehlkoSensor(coord, 1, by_key[key])
        assert entity.native_value == expected
        assert entity.options == ["weak", "moderate", "strong"]
    # A level newer than this release is still a valid state.
    sample_gen.hub["wifiStrength"] = "Excellent"
    entity = sensor_mod.RehlkoSensor(coord, 1, by_key["wifi_strength"])
    assert entity.native_value == "excellent"
    assert "excellent" in entity.options


def test_devices_do_not_impose_areas_and_the_account_is_a_service(
    sample_gen: GeneratorData,
) -> None:
    from homeassistant.helpers.device_registry import DeviceEntryType

    from custom_components.rehlko_energy import entity as entity_mod

    coord = FakeCoordinator(sample_gen)
    # A hardcoded English area name would be created in every user's home, in any language.
    assert "suggested_area" not in entity_mod.generator_device_info(sample_gen)
    assert "suggested_area" not in entity_mod.ats_device_info(sample_gen)
    assert entity_mod.account_device_info(coord)["entry_type"] is DeviceEntryType.SERVICE


def test_unique_ids_carry_the_account(sample_gen: GeneratorData) -> None:
    """Two accounts that share a generator must not produce the same entity IDs."""
    coord = FakeCoordinator(sample_gen)
    first = sensor_mod.RehlkoSensor(coord, 1, sensor_mod.SENSORS[0])
    assert first.unique_id == "e1-1-utility_voltage"
    coord.config_entry = SimpleNamespace(entry_id="e2", title="other")
    assert sensor_mod.RehlkoSensor(coord, 1, sensor_mod.SENSORS[0]).unique_id != first.unique_id


def test_catch_all_entities_are_created_disabled(sample_gen: GeneratorData) -> None:
    coord = FakeCoordinator(sample_gen)
    assert not sensor_mod.ExtraFieldSensor(
        coord, 1, "device", "someNewField"
    ).entity_registry_enabled_default
    assert not bs.ExtraFlagSensor(
        coord, 1, "details", "someNewFlag"
    ).entity_registry_enabled_default
    # The entities people use stay on.
    by_key = {d.key: d for d in sensor_mod.SENSORS}
    assert sensor_mod.RehlkoSensor(
        coord, 1, by_key["battery_voltage"]
    ).entity_registry_enabled_default


def test_energy_is_the_load_added_up_between_polls(sample_gen: GeneratorData) -> None:
    coord = FakeCoordinator(sample_gen)
    sensor = sensor_mod.EnergyProducedSensor(coord, 1)
    start = datetime(2026, 11, 13, 12, 0, tzinfo=UTC)

    def poll(seconds: int, watts: float | None, **changes) -> float:
        sample_gen.details_updated = start + timedelta(seconds=seconds)
        sample_gen.details["generatorLoadW"] = watts
        for key, value in changes.items():
            setattr(sample_gen, key, value)
        sensor._integrate()
        return sensor.native_value

    assert poll(0, 6000) == 0  # one reading is not yet an interval
    assert poll(30, 6000) == pytest.approx(0.05)  # 6 kW for 30 s
    assert poll(60, 3000) == pytest.approx(0.05 + 0.0375)  # trapezoid: 4.5 kW average
    assert poll(60, 3000) == pytest.approx(0.0875)  # the same reading again adds nothing
    # Readings lost: the gap is not bridged, and counting resumes from the next reading.
    assert poll(90, 3000, details_available=False) == pytest.approx(0.0875)
    assert poll(120, 3000, details_available=True) == pytest.approx(0.0875)
    assert poll(150, 3000) == pytest.approx(0.0875 + 0.025)
    # A stretch far longer than polling allows (a suspended host) is not counted either.
    assert poll(150 + 3600, 3000) == pytest.approx(0.1125)
    # No reading is not zero watts.
    assert poll(150 + 3630, None) == pytest.approx(0.1125)
    assert sensor.device_class == "energy"
    assert sensor.state_class == "total_increasing"


def test_energy_counts_nothing_while_the_engine_is_stopped(sample_gen: GeneratorData) -> None:
    coord = FakeCoordinator(sample_gen)
    sensor = sensor_mod.EnergyProducedSensor(coord, 1)
    start = datetime(2026, 11, 13, 12, 0, tzinfo=UTC)
    sample_gen.device["status"] = "ReadyToRun"
    sample_gen.details.update(engineState="Standby", engineSpeedRpm=0, generatorLoadW=40)
    for seconds in (0, 60, 120):
        sample_gen.details_updated = start + timedelta(seconds=seconds)
        sensor._integrate()
    assert sensor.native_value == 0
    # It starts: the first running interval is averaged from zero.
    sample_gen.device["status"] = "Running"
    sample_gen.details.update(engineState="Running", engineSpeedRpm=3600, generatorLoadW=7200)
    sample_gen.details_updated = start + timedelta(seconds=180)
    sensor._integrate()
    assert sensor.native_value == pytest.approx(0.06)
