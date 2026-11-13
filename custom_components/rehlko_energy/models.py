"""The coordinator's snapshot of an account, and derived generator state.

Payloads are kept as the service sent them (plain dicts) so nothing the API reports is
lost; the accessors here only interpret them. Field names are the API's (docs/API.md).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from .api.util import as_float, first, plain_ip
from .const import DEFAULT_NOMINAL_VOLTAGE, UTILITY_PRESENT_FRACTION

# Genset (engine) states in which the engine is turning.
RUNNING_ENGINE_STATES = frozenset(
    {
        "CrankOn",
        "CrankPause",
        "Idle",
        "Running",
        "CoolDown",
        "Stopping",
        "PerformingLoadedTest",
        "PerformingUnloadedTest",
        "PerformingVariableSpeedExercise",
        "PerformingLoadedExercise",
        "PerformingUnloadedFullSpeedExercise",
        "PerformingFullSpeedDiagnostics",
        "PerformingEcoCycle",
        "FaultCoolDown",
        "Unloading",
        "Synchronizing",
        "Choke",
        "Preheat",
        "StartDelay",
    }
)
EXERCISE_ENGINE_STATES = frozenset(
    {
        "PerformingVariableSpeedExercise",
        "PerformingLoadedExercise",
        "PerformingUnloadedFullSpeedExercise",
        "PerformingEcoCycle",
        "PerformingLoadedTest",
        "PerformingUnloadedTest",
        "PerformingFullSpeedDiagnostics",
    }
)
# Values that the generated client uses for "not set".
EMPTY_ENUMS = frozenset(
    {None, "", "None", "Unknown", "UnknownUndefined", "swaggerGeneratedUnknown"}
)

# Products whose remote exercise scheduling the app disables.
NO_EXERCISE_SCHEDULING_PRODUCTS = frozenset({"Apm402"})


@dataclass(slots=True)
class GeneratorData:
    """Everything known about one generator (a KEM "device")."""

    device_id: int
    home: dict[str, Any]
    device: dict[str, Any]
    details: dict[str, Any] = field(default_factory=dict)
    alerts: list[dict[str, Any]] = field(default_factory=list)
    events: list[dict[str, Any]] = field(default_factory=list)
    maintenance_notes: list[dict[str, Any]] = field(default_factory=list)
    notifications: list[dict[str, Any]] = field(default_factory=list)
    cell_plan: dict[str, Any] | None = None
    details_updated: datetime | None = None
    feeds_updated: datetime | None = None
    details_available: bool = True
    refreshed_feeds: set[str] = field(default_factory=set)

    # ------------------------------------------------------------- raw access
    def get(self, key: str) -> Any:
        """A field from the details payload, else from the device summary."""
        value = self.details.get(key)
        return value if value is not None else self.device.get(key)

    @property
    def exercise(self) -> dict[str, Any]:
        return self.details.get("exercise") or {}

    @property
    def load_shed(self) -> dict[str, Any]:
        return self.details.get("loadShed") or {}

    @property
    def pim(self) -> dict[str, Any]:
        return self.details.get("pim") or {}

    @property
    def ats(self) -> dict[str, Any]:
        return self.details.get("ats") or {}

    @property
    def generators(self) -> list[dict[str, Any]]:
        value = self.details.get("generators")
        return value if isinstance(value, list) else []

    @property
    def hub(self) -> dict[str, Any]:
        return self.device.get("hubData") or {}

    @property
    def service_agreement(self) -> dict[str, Any]:
        return self.details.get("serviceAgreement") or {}

    @property
    def firmware_update(self) -> dict[str, Any]:
        return self.details.get("firmwareUpdate") or {}

    @property
    def install_progress(self) -> dict[str, Any]:
        return self.details.get("installProgress") or {}

    # ------------------------------------------------------------- identity
    @property
    def serial_number(self) -> str | None:
        return self.device.get("serialNumber")

    @property
    def name(self) -> str:
        return (
            self.device.get("displayName")
            or self.home.get("name")
            or f"Generator {self.serial_number or self.device_id}"
        )

    @property
    def source_host(self) -> str | None:
        return self.device.get("deviceHost")

    @property
    def model(self) -> str | None:
        return first(self.device.get("modelDisplayName"), self.device.get("model"))

    @property
    def ip_address(self) -> str | None:
        """The address the controller connects from, without the port the service adds."""
        return plain_ip(self.device.get("deviceIpAddress"))

    # ------------------------------------------------------------- derived state
    @property
    def is_connected(self) -> bool:
        return bool(first(self.device.get("isConnected"), self.details.get("isConnected")))

    @property
    def status(self) -> str | None:
        return self.device.get("status")

    @property
    def engine_state(self) -> str | None:
        return self.get("engineState")

    @property
    def is_running(self) -> bool:
        if self.status in ("Running", "RunningExercise"):
            return True
        if self.engine_state in RUNNING_ENGINE_STATES:
            return True
        rpm = as_float(self.details.get("engineSpeedRpm"))
        return rpm is not None and rpm > 300

    @property
    def is_exercising(self) -> bool:
        if self.status == "RunningExercise" or self.engine_state in EXERCISE_ENGINE_STATES:
            return True
        return self.exercise.get("runningMode") not in EMPTY_ENUMS

    @property
    def on_generator_power(self) -> bool:
        return self.details.get("powerSource") == "Generator"

    @property
    def nominal_voltage(self) -> float:
        return as_float(self.details.get("setOutputVoltageV")) or DEFAULT_NOMINAL_VOLTAGE

    @property
    def utility_present(self) -> bool | None:
        volts = as_float(self.details.get("utilityVoltageV"))
        if volts is not None:
            return volts >= self.nominal_voltage * UTILITY_PRESENT_FRACTION
        source = self.details.get("powerSource")
        if source == "Utility":
            return True
        if source == "Generator":
            return False
        return None

    @property
    def ready_to_run(self) -> bool:
        return self.status == "ReadyToRun"

    @property
    def has_schedule(self) -> bool:
        ex = self.exercise
        return (
            bool(ex)
            and ex.get("frequency") not in EMPTY_ENUMS
            and ex.get("mode") not in EMPTY_ENUMS
        )

    @property
    def e_stop_engaged(self) -> bool:
        for alert in self.alerts:
            if alert.get("deviceEventId") == "EmergencyStop" or alert.get("isEStopEvent"):
                return True
        return any(n.get("isEStopEvent") for n in self.notifications[:1])

    @property
    def is_active(self) -> bool:
        """Worth polling quickly: running, exercising, or the home is on generator power."""
        return (
            self.is_running
            or self.is_exercising
            or self.on_generator_power
            or (self.utility_present is False)
        )

    @property
    def supports_exercise_scheduling(self) -> bool:
        return self.device.get("product") not in NO_EXERCISE_SCHEDULING_PRODUCTS

    @property
    def supports_next_exercise_datetime(self) -> bool:
        return bool(self.exercise.get("supportsNextExerciseDateTimeParam"))

    def peripheral_parameters(self) -> list[tuple[str, dict[str, Any]]]:
        """`(peripheral, parameter)` for every load-module and PIM parameter."""
        out: list[tuple[str, dict[str, Any]]] = []
        for kind, block in (("loadShed", self.load_shed), ("pim", self.pim)):
            for param in block.get("parameters") or []:
                if isinstance(param, dict) and param.get("definitionId") is not None:
                    out.append((kind, param))
        return out


@dataclass(slots=True)
class AccountData:
    """One config entry's view of its account."""

    me: dict[str, Any] = field(default_factory=dict)
    homes: list[dict[str, Any]] = field(default_factory=list)
    generators: dict[int, GeneratorData] = field(default_factory=dict)
    notification_settings: dict[str, Any] | None = None
