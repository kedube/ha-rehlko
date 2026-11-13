"""GeneratorData derivations: running, exercising, utility presence, peripherals, E-Stop."""

from __future__ import annotations

from custom_components.rehlko_energy.models import GeneratorData


def gen(device: dict | None = None, details: dict | None = None, **kw) -> GeneratorData:
    return GeneratorData(
        device_id=1,
        home=kw.get("home", {"name": "Home"}),
        device=device or {},
        details=details or {},
        alerts=kw.get("alerts", []),
    )


def test_name_prefers_display_name() -> None:
    assert gen({"displayName": "Shed Genset"}).name == "Shed Genset"
    # Falls back to the home name, then to a serial-based name when there is no home name.
    assert gen({"serialNumber": "SN9"}, home={}).name == "Generator SN9"
    assert gen({"serialNumber": "SN9"}).name == "Home"


def test_is_running_from_status_state_or_rpm() -> None:
    assert gen(details={"engineState": "Running"}).is_running
    assert gen({"status": "Running"}).is_running
    assert gen(details={"engineSpeedRpm": 1800}).is_running
    assert not gen(details={"engineSpeedRpm": 0, "engineState": "Off"}).is_running
    assert not gen({"status": "ReadyToRun"}).is_running


def test_is_exercising() -> None:
    assert gen({"status": "RunningExercise"}).is_exercising
    assert gen(details={"engineState": "PerformingLoadedExercise"}).is_exercising
    assert gen(details={"exercise": {"runningMode": "Unloaded"}}).is_exercising
    assert not gen(details={"exercise": {"runningMode": "None"}}).is_exercising
    assert not gen(details={"exercise": {"runningMode": "swaggerGeneratedUnknown"}}).is_exercising


def test_utility_present_from_voltage() -> None:
    assert gen(details={"utilityVoltageV": 241, "setOutputVoltageV": 240}).utility_present is True
    assert gen(details={"utilityVoltageV": 0, "setOutputVoltageV": 240}).utility_present is False
    # Falls back to powerSource when no voltage is reported.
    assert gen(details={"powerSource": "Utility"}).utility_present is True
    assert gen(details={"powerSource": "Generator"}).utility_present is False
    assert gen(details={}).utility_present is None


def test_on_generator_power_and_active() -> None:
    g = gen(details={"powerSource": "Generator", "utilityVoltageV": 0, "setOutputVoltageV": 240})
    assert g.on_generator_power
    assert g.is_active  # outage / on generator power -> poll fast
    idle = gen(
        {"status": "ReadyToRun"},
        {"powerSource": "Utility", "utilityVoltageV": 241, "setOutputVoltageV": 240},
    )
    assert not idle.is_active


def test_has_schedule() -> None:
    assert gen(details={"exercise": {"frequency": "Weekly", "mode": "Unloaded"}}).has_schedule
    assert not gen(details={"exercise": {"frequency": "None", "mode": "None"}}).has_schedule
    assert not gen(details={}).has_schedule


def test_ready_to_run_and_scheduling_support() -> None:
    assert gen({"status": "ReadyToRun"}).ready_to_run
    assert gen({"product": "Rdc2"}).supports_exercise_scheduling
    assert not gen({"product": "Apm402"}).supports_exercise_scheduling


def test_estop_from_alert_or_notification() -> None:
    assert gen(alerts=[{"deviceEventId": "EmergencyStop"}]).e_stop_engaged
    assert gen(alerts=[{"deviceEventId": "Other", "isEStopEvent": True}]).e_stop_engaged
    g = gen()
    g.notifications = [{"isEStopEvent": True}]
    assert g.e_stop_engaged
    assert not gen(alerts=[{"deviceEventId": "Other"}]).e_stop_engaged


def test_peripheral_parameters_flattens_loadshed_and_pim() -> None:
    g = gen(
        details={
            "loadShed": {
                "isConnected": True,
                "parameters": [{"definitionId": 1, "displayName": "AC"}],
            },
            "pim": {"parameters": [{"definitionId": 2, "displayName": "Pump"}, {"noId": True}]},
        }
    )
    params = g.peripheral_parameters()
    assert [(k, p["definitionId"]) for k, p in params] == [("loadShed", 1), ("pim", 2)]


def test_source_host_and_model() -> None:
    g = gen({"deviceHost": "REC", "modelDisplayName": "24RCL", "model": "Model24RCL"})
    assert g.source_host == "REC"
    assert g.model == "24RCL"
    assert gen({"model": "Model24RCL"}).model == "Model24RCL"


def test_get_prefers_details_then_device() -> None:
    g = gen({"connectionType": "Ethernet"}, {"connectionType": "KohlerWifi"})
    assert g.get("connectionType") == "KohlerWifi"
    assert gen({"connectionType": "Ethernet"}, {}).get("connectionType") == "Ethernet"
