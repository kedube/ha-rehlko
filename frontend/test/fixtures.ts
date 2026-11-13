import type { Generator, Snapshot } from "../src/types";

export function sampleGenerator(overrides: Partial<Generator> = {}): Generator {
  return {
    entry_id: "account-1", device_id: 1, available: true, ha_device_id: "ha-device-1",
    name: "Home generator", serial_number: "DEMO-001", home: {},
    device: { status: "ReadyToRun", modelDisplayName: "26RCA", model: "Model26RCAA" },
    details: {
      powerSource: "Utility", utilityVoltageV: 240, generatorVoltageAvgV: 0,
      engineSpeedRpm: 0, batteryVoltageV: 13.4, totalRuntimeHours: 182.4,
      exercise: { frequency: "Weekly", mode: "Unloaded", durationMinutes: 20,
        nextStartTimestamp: "2026-11-22T14:00:00", supportsNextExerciseDateTimeParam: true },
    },
    alerts: [], events: [], maintenance_notes: [], notifications: [], cell_plan: null,
    derived: {
      is_connected: true, is_running: false, is_exercising: false,
      on_generator_power: false, utility_present: true, ready_to_run: true,
      has_schedule: true, e_stop_engaged: false, nominal_voltage: 240,
      supports_exercise_scheduling: true, supports_next_exercise_datetime: true,
    },
    entities: {}, details_updated: new Date().toISOString(), feeds_updated: null,
    ...overrides,
  };
}

export function sampleSnapshot(generators = [sampleGenerator()]): Snapshot {
  return { generators, accounts: [{ entry_id: "account-1", title: "Demo account", loaded: true,
    last_update_success: true, notification_settings: { sendWarnings: true },
    notification_entities: { sendWarnings: "switch.demo_warnings" } }] };
}
