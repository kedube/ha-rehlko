#!/usr/bin/env python3
"""Build strings.json and every file in translations/, and check the panel's locales.

English is written here; enum state names are derived from the API vocabulary
(custom_components/rehlko_energy/api/vocabulary.py), so a new wire value only needs adding
there. Every other language is a catalogue in scripts/locales/<language>.json:

    {"strings": {"<English text>": "<translation>", ...},
     "overrides": {"entity.sensor.status.state.off": "<translation for that one place>"}}

`strings` is keyed by the English text, so a phrase used in several places is translated once
and a reworded English phrase is flagged instead of silently keeping a stale translation.
`overrides` (optional) is keyed by a dotted path for the rare word that needs a different
translation in one place. Text without a translation is left out of the generated file, and
Home Assistant shows the English for it.

Run from the repository root:

    python3 scripts/build_translations.py              # write everything
    python3 scripts/build_translations.py --check      # CI: fail if anything is stale or invalid
    python3 scripts/build_translations.py --template   # an empty catalogue for a new language
    python3 scripts/build_translations.py --check --strict --lang es   # es must be complete

The sidebar panel keeps its own locales in frontend/src/locales/<language>.json (keyed by
message id, with en.json as the source). They are validated here too, so one command covers
both halves.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
COMPONENT = ROOT / "custom_components" / "rehlko_energy"
LOCALES = ROOT / "scripts" / "locales"
PANEL_LOCALES = ROOT / "frontend" / "src" / "locales"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


# Standalone modules (no Home Assistant imports needed).
V = _load("vocabulary", COMPONENT / "api" / "vocabulary.py")
U = _load("util", COMPONENT / "api" / "util.py")
T = _load("texts", COMPONENT / "texts.py")

# Nicer names than the mechanical split, where it matters.
OVERRIDES = {
    "ready_to_run": "Ready to run",
    "switch_state_off": "Switched off",
    "running_exercise": "Exercising",
    "every_other_week": "Every other week",
    "unloaded_full_speed": "Unloaded, full speed",
    "loaded_full_speed": "Loaded, full speed",
    "eco_exercise": "EcoExercise",
    "kohler_wifi": "Kohler Wi-Fi",
    "other_wifi": "Other Wi-Fi",
    "kohler_cell_kit": "Kohler cellular kit",
    "ism": "ISM radio",
    "liquid_propane": "Liquid propane (LP)",
    "natural_gas": "Natural gas",
    "unknown_undefined": "Unknown",
    "cool_down": "Cooling down",
    "fault_cool_down": "Fault cool-down",
    "crank_on": "Cranking",
    "crank_pause": "Crank rest",
    "ecm_powered": "ECM powered",
    "near_data_limit": "Near data limit",
    "reached_data_limit": "Data limit reached",
    "in_progress": "In progress",
    "renewal_failed": "Renewal failed",
    "missing_data": "Missing data",
    "clear_sky": "Clear sky",
    "few_clouds": "Few clouds",
    "scattered_clouds": "Scattered clouds",
    "broken_clouds": "Broken clouds",
    "shower_rain": "Showers",
    "system_status_change": "System status change",
    "maintenance_notice": "Maintenance notice",
    "long_running_notice": "Long-running notice",
    "engine_started_notice": "Engine started",
    "engine_stopped_notice": "Engine stopped",
    "exercise_started_notice": "Exercise started",
    "exercise_ended_notice": "Exercise ended",
    "online_notice": "Back online",
    "offline_notice": "Went offline",
    "performing_eco_cycle": "Running EcoExercise",
    "stopped_by_generator_management": "Stopped by generator management",
    "protective_relay_tripped_contactor": "Protective relay tripped",
}


def states(values) -> dict[str, str]:
    out: dict[str, str] = {}
    for value in values:
        slug = U.slugify(value)
        if slug and slug not in out:
            out[slug] = OVERRIDES.get(slug) or U.humanize(value)
    return out


def enum_sensor(name: str, values) -> dict:
    return {"name": name, "state": states(values)}


SENSOR = {
    "utility_voltage": {"name": "Utility voltage"},
    "generator_voltage": {"name": "Generator voltage"},
    "generator_load": {"name": "Generator load"},
    "generator_load_percent": {"name": "Generator load (of rated)"},
    "energy_produced": {"name": "Energy produced"},
    "set_output_voltage": {"name": "Rated output voltage"},
    "power_source": enum_sensor("Power source", V.POWER_SOURCE),
    "engine_speed": {"name": "Engine speed"},
    "engine_frequency": {"name": "Generator frequency"},
    "engine_oil_pressure": {"name": "Oil pressure"},
    "engine_coolant_temperature": {"name": "Coolant temperature"},
    "lube_oil_temperature": {"name": "Lube oil temperature"},
    "engine_compartment_temperature": {"name": "Engine compartment temperature"},
    "engine_state": enum_sensor("Engine state", V.GENSET_STATE),
    "fuel_level": {"name": "Fuel level"},
    "battery_voltage": {"name": "Battery voltage"},
    "controller_temperature": {"name": "Controller temperature"},
    "controller_clock": {"name": "Controller clock"},
    "status": enum_sensor("Status", V.DEVICE_STATUS),
    "switch_state": enum_sensor("Mode switch", V.SWITCH_STATE),
    "shutdown_reason": {"name": "Shutdown reason"},
    "alert_count": {"name": "Active alerts"},
    "total_runtime": {"name": "Total runtime"},
    "total_operation": {"name": "Total operation"},
    "runtime_since_maintenance": {"name": "Runtime since maintenance"},
    "last_run": {"name": "Last run"},
    "last_maintenance": {"name": "Last maintenance"},
    "next_maintenance": {"name": "Next maintenance"},
    "maintenance_period": {"name": "Maintenance interval"},
    "last_maintenance_note": {"name": "Latest maintenance note"},
    "next_exercise": {"name": "Next exercise"},
    "last_exercise_start": {"name": "Last exercise started"},
    "last_exercise_end": {"name": "Last exercise ended"},
    "exercise_running_mode": enum_sensor("Exercise in progress", V.EXERCISE_MODE),
    "last_event": {"name": "Last activity"},
    "last_notification": {"name": "Last notification"},
    "weather_temperature": {"name": "Outdoor temperature"},
    "weather_condition": enum_sensor("Weather", V.WEATHER_CONDITION),
    "model": {"name": "Model"},
    "product": {"name": "Controller product"},
    "controller_type": {"name": "Controller type"},
    "firmware_version": {"name": "Firmware version"},
    "current_firmware": {"name": "Firmware build"},
    "fuel_type": enum_sensor("Fuel type", V.FUEL_TYPE),
    "cooling_type": enum_sensor("Cooling", V.COOLING_TYPE),
    "connection_type": enum_sensor("Connection", V.CONNECTION_TYPE),
    "device_ip_address": {"name": "IP address"},
    "server_ip_address": {"name": "Server IP address"},
    "mac_address": {"name": "MAC address"},
    "last_connected": {"name": "Last connected"},
    "status_updated": {"name": "Status updated"},
    "parameters_updated": {"name": "Parameters updated"},
    "uptime_percent": {"name": "Connection uptime"},
    "remote_reset_counter": {"name": "Remote reset countdown"},
    "wifi_strength": enum_sensor("Wi-Fi signal", V.SIGNAL_STRENGTH),
    "cellular_strength": enum_sensor("Cellular signal", V.SIGNAL_STRENGTH),
    "site_address": {"name": "Site address"},
    "dealer": {"name": "Dealer"},
    "service_agreement_status": enum_sensor("Service agreement", V.SERVICE_AGREEMENT_STATUS),
    "cellular_data_status": enum_sensor("Cellular data", V.CELLULAR_DATA_STATUS),
    "cellular_data_used": {"name": "Cellular data used"},
    "cellular_expiry": {"name": "Cellular plan expires"},
    "cellular_installed": {"name": "Cellular kit installed"},
    "cell_kit_payment_status": enum_sensor("Cellular plan payment", V.CELL_KIT_PAYMENT_STATUS),
    "cell_data_remaining": {"name": "Cellular data remaining"},
    "scheduled_firmware_update": {"name": "Scheduled firmware update"},
    "install_progress": {"name": "Installation progress"},
    "ats_power_source": enum_sensor("Transfer switch position", V.POWER_SOURCE),
    "ats_connection_type": enum_sensor("Transfer switch link", V.SUB_DEVICE_CONNECTION_TYPE),
    "ats_signal_strength": enum_sensor("Transfer switch signal", V.SIGNAL_STRENGTH),
    "load_module_parameter": {"name": "Load module {name}"},
    "pim_parameter": {"name": "PIM {name}"},
    "extra_field": {"name": "{field}"},
}

BINARY_SENSOR = {
    "connected": "Cloud connection",
    "utility_power": "Utility power",
    "on_generator_power": "On generator power",
    "running": "Running",
    "exercising": "Exercising",
    "ready_to_run": "Ready to run",
    "not_in_auto": "Not in Auto",
    "oil_pressure_problem": "Oil pressure",
    "maintenance_due": "Maintenance due",
    "active_alerts": "Alerts",
    "critical_fault": "Critical fault",
    "e_stop": "Emergency stop",
    "exercise_scheduled": "Exercise scheduled",
    "service_agreement": "Service agreement",
    "cellular_kit_online": "Cellular kit",
    "wifi_connected": "Wi-Fi",
    "cellular_connected": "Cellular",
    "load_module_connected": "Load module",
    "pim_connected": "PIM",
    "firmware_update_available": "Firmware update available",
    "extra_flag": "{field}",
}

PERIPHERAL = {
    "load_module_setting": {"name": "Load module {name}"},
    "pim_setting": {"name": "PIM {name}"},
}

EXERCISE_MODES = ("Unloaded", "UnloadedFullSpeed", "LoadedFullSpeed", "EcoExercise")
EXERCISE_FREQUENCIES = ("Weekly", "EveryOtherWeek", "Monthly")

POWER_EVENTS = {
    "utility_lost": "Utility power lost",
    "utility_restored": "Utility power restored",
    "generator_started": "Generator started",
    "generator_stopped": "Generator stopped",
    "transferred_to_generator": "Load transferred to generator",
    "transferred_to_utility": "Load transferred to utility",
}


def event(name: str, types: dict[str, str]) -> dict:
    return {"name": name, "state_attributes": {"event_type": {"state": types}}}


def field(name: str, description: str) -> dict:
    return {"name": name, "description": description}


DEVICE_FIELD = field("Generator", "The generator (or its transfer switch) to act on.")
MODE_FIELD = field("Mode", "Unloaded, unloaded full speed, loaded full speed, or EcoExercise.")

APP_CREDENTIALS = {
    "name": "App credentials",
    "description": "The OAuth client ID, client secret and API key from the Energy Mgmt. app's configuration.",
    "data": {
        "client_id": "OAuth client ID",
        "client_secret": "OAuth client secret",
        "api_key": "API key",
    },
    "data_description": {
        "client_id": "CLIENT_ID in the app's configuration file.",
        "client_secret": "CLIENT_SECRET in the app's configuration file.",
        "api_key": "API_KEY in the app's configuration file.",
    },
}
PASSWORD_HELP = (
    "Stored in Home Assistant so the integration can sign in again when its session expires."
)
# Reconfiguring: the stored secret and API key are not shown, and an empty field keeps them.
KEEP_STORED = "Leave empty to keep the stored value."
STORED_APP_CREDENTIALS = {
    **APP_CREDENTIALS,
    "data_description": {
        "client_id": APP_CREDENTIALS["data_description"]["client_id"],
        "client_secret": KEEP_STORED,
        "api_key": KEEP_STORED,
    },
}

STRINGS = {
    "config": {
        "step": {
            "user": {
                "title": "Sign in to Rehlko Energy Management",
                "description": "Use the email and password you use in the Energy Mgmt. (formerly KOHLER Energy Management) app. The app credentials below identify the app to Rehlko's sign-in service; see the integration's documentation for where to find them.",
                "data": {"username": "Email", "password": "Password"},
                "data_description": {
                    "username": "The email address of your Rehlko / Kohler Energy Management account.",
                    "password": PASSWORD_HELP,
                },
                "sections": {"app_credentials": APP_CREDENTIALS},
            },
            "reauth_confirm": {
                "title": "Sign in again",
                "description": "Rehlko asked for the password for {username} again.",
                "data": {"password": "Password"},
                "data_description": {"password": PASSWORD_HELP},
            },
            "reconfigure": {
                "title": "Update credentials",
                "description": "Update the password or the app credentials for {username} (for example after an app update changed them).",
                "data": {"password": "Password"},
                "data_description": {"password": PASSWORD_HELP},
                "sections": {"app_credentials": STORED_APP_CREDENTIALS},
            },
        },
        "error": {
            "invalid_auth": "The email or password was not accepted.",
            "sign_in_denied": "Rehlko's sign-in service refused a password sign-in for this account. That happens when the account requires multi-factor authentication, which this integration cannot complete.",
            "invalid_app_credentials": "The sign-in service rejected the app's client ID or client secret.",
            "invalid_api_key": "Signed in, but the API rejected the request; check the API key.",
            "cannot_connect": "Could not reach the Rehlko service.",
            "no_generators": "Signed in, but this account has no generators.",
            "unknown": "Unexpected error; see the logs.",
        },
        "abort": {
            "already_configured": "This account is already configured.",
            "reauth_successful": "Signed in again.",
            "reconfigure_successful": "Credentials updated.",
            "wrong_account": "Those credentials belong to a different account.",
        },
    },
    "options": {
        "step": {
            "init": {
                "title": "Rehlko Energy Management options",
                "data": {
                    "scan_interval": "Polling interval in standby",
                    "active_scan_interval": "Polling interval while running or during an outage",
                    "feed_interval": "Activity log, alerts and notifications interval",
                    "notification_limit": "Notifications to fetch per generator",
                    "sidebar_panel": "Show the Generator panel in the sidebar",
                    "extra_diagnostic_entities": "Create diagnostic entities for every other API field",
                },
                "data_description": {
                    "scan_interval": "How often to read the generator while it is idle.",
                    "active_scan_interval": "Used while the engine runs, during an exercise, or when the home is on generator power.",
                    "feed_interval": "These lists change rarely; a longer interval means fewer requests.",
                    "notification_limit": "The newest notifications are fetched first.",
                    "sidebar_panel": "The panel is visible to administrators only.",
                    "extra_diagnostic_entities": "They are created disabled, so nothing the service reports is hidden and nothing is recorded until you enable it on the device page.",
                },
            }
        }
    },
    "selector": {
        "exercise_mode": {"options": states(EXERCISE_MODES)},
        "exercise_frequency": {"options": states(EXERCISE_FREQUENCIES)},
        "controller_kind": {"options": {"generator": "Generator", "ats": "Transfer switch"}},
    },
    "entity": {
        "sensor": SENSOR,
        "binary_sensor": {k: {"name": v} for k, v in BINARY_SENSOR.items()},
        "button": {
            "start_exercise": {"name": "Start exercise"},
            "stop_exercise": {"name": "Stop exercise"},
            "sync_controller_clock": {"name": "Sync controller clock"},
            "refresh": {"name": "Refresh"},
        },
        "select": {
            "exercise_mode": {"name": "Exercise mode", "state": states(EXERCISE_MODES)},
            "exercise_frequency": {
                "name": "Exercise frequency",
                "state": states(EXERCISE_FREQUENCIES),
            },
        },
        "number": {"exercise_duration": {"name": "Exercise duration"}, **PERIPHERAL},
        "datetime": {"next_exercise_start": {"name": "Next exercise start"}},
        "switch": {
            "notify_shutdowns": {"name": "Shutdown notifications"},
            "notify_warnings": {"name": "Warning notifications"},
            "notify_running": {"name": "Generator running notifications"},
            "notify_notices": {"name": "General notices"},
            "notify_connection": {"name": "Connection notifications"},
            "notify_maintenance": {"name": "Maintenance reminders"},
            "notify_long_running": {"name": "Long-running notifications"},
            "notify_emails": {"name": "Email notifications"},
            "notify_push": {"name": "Push notifications"},
            "notify_other": {"name": "{name} notifications"},
            "auto_firmware_update": {"name": "Automatic firmware updates"},
            **PERIPHERAL,
        },
        "text": {"generator_name": {"name": "Generator name"}, **PERIPHERAL},
        "event": {
            "activity": event("Activity", states(V.DEVICE_EVENT_LEVEL)),
            "alerts": event("Alert", {"raised": "Raised", "cleared": "Cleared"}),
            "notifications": event("Notification", states((*V.NOTIFICATION_TYPE, "Notice"))),
            "power": event("Power event", POWER_EVENTS),
        },
        # The calendar's event titles and the update's summary are rendered by the
        # integration (texts.py); their translations live with the attributes they fill.
        "calendar": {
            "schedule": {
                "name": "Exercise and maintenance",
                "state_attributes": {
                    "message": {"state": dict(T.CALENDAR_SUMMARY)},
                    "description": {"state": dict(T.CALENDAR_DESCRIPTION)},
                },
            }
        },
        "update": {
            "firmware": {
                "name": "Controller firmware",
                "state_attributes": {"release_summary": {"state": dict(T.FIRMWARE_SUMMARY)}},
            }
        },
    },
    "exceptions": {
        "unknown_generator": {"message": "Generator {device_id} is not part of this account."},
        "auth_failed": {
            "message": "Rehlko rejected the stored credentials; re-authentication has been requested."
        },
        "api_error": {
            "message": "The Rehlko service refused the request (HTTP {status}): {message}"
        },
        "unavailable": {"message": "The Rehlko service is unavailable: {message}"},
        "offline": {
            "message": "{name} is offline; remote actions are unavailable until it reconnects."
        },
        "e_stop": {
            "message": "The emergency stop is engaged on {name}. Remote start and remote exercise are unavailable until it is reset at the generator."
        },
        "not_ready": {
            "message": "{name} is not ready to run (status: {status}); starting an exercise is disabled."
        },
        "no_scheduling": {
            "message": "Remote exercise scheduling is not available for {name}'s controller."
        },
        "empty_note": {"message": "The maintenance note is empty."},
        "empty_name": {"message": "The name is empty."},
        "read_only": {"message": "{name} is read-only."},
        "device_not_found": {"message": "Device {device_id} was not found."},
        "not_a_generator": {"message": "Device {device_id} is not a Rehlko generator."},
        "entry_not_loaded": {"message": "The account for device {device_id} is not loaded."},
        "no_serial": {"message": "The service did not report a serial number for that controller."},
    },
    "services": {
        "start_exercise": {
            "name": "Start exercise",
            "description": 'Start an exercise run now (the app\'s "Start an exercise now"). The generator must be online, in Auto and ready to run.',
            "fields": {
                "device_id": DEVICE_FIELD,
                "mode": field("Mode", "How to run it; defaults to the scheduled exercise's mode."),
            },
        },
        "stop_exercise": {
            "name": "Stop exercise",
            "description": "Stop the exercise that is running.",
            "fields": {"device_id": DEVICE_FIELD},
        },
        "set_exercise_schedule": {
            "name": "Set exercise schedule",
            "description": "Create or change the recurring exercise. Fields left out keep their current value.",
            "fields": {
                "device_id": DEVICE_FIELD,
                "frequency": field("Frequency", "Weekly, every other week, or monthly."),
                "mode": MODE_FIELD,
                "duration": field("Duration", "Run time in minutes."),
                "next_start": field(
                    "Next start",
                    "When the next exercise starts (only on controllers that allow choosing it).",
                ),
            },
        },
        "delete_exercise_schedule": {
            "name": "Delete exercise schedule",
            "description": "Remove the recurring exercise.",
            "fields": {"device_id": DEVICE_FIELD},
        },
        "add_maintenance_note": {
            "name": "Add maintenance note",
            "description": "Add an entry to the generator's maintenance history.",
            "fields": {"device_id": DEVICE_FIELD, "note": field("Note", "What was done.")},
        },
        "sync_controller_clock": {
            "name": "Sync controller clock",
            "description": "Set the controller's clock (to now, unless a time is given).",
            "fields": {
                "device_id": DEVICE_FIELD,
                "timestamp": field("Time", "The time to set; defaults to now."),
            },
        },
        "set_peripheral_value": {
            "name": "Set load module / PIM value",
            "description": "Write one load-module or PIM parameter.",
            "fields": {
                "device_id": DEVICE_FIELD,
                "definition_id": field(
                    "Definition ID", "The parameter's definition ID (an entity attribute)."
                ),
                "value": field("Value", "The value to write."),
            },
        },
        "rename_peripheral": {
            "name": "Rename load / PIM item",
            "description": "Change a load-module or PIM parameter's display name.",
            "fields": {
                "device_id": DEVICE_FIELD,
                "definition_id": field("Definition ID", "The parameter's definition ID."),
                "name": field("Name", "The new name."),
            },
        },
        "refresh": {
            "name": "Refresh",
            "description": "Poll everything now, including the activity log and maintenance history.",
            "fields": {
                "device_id": field(
                    "Generator", "Only this generator's account; all accounts if omitted."
                )
            },
        },
        "get_activity_log": {
            "name": "Get activity log",
            "description": "Return the generator's activity (event) log.",
            "fields": {
                "device_id": DEVICE_FIELD,
                "limit": field("Limit", "The most entries to return, newest first."),
            },
        },
        "get_alerts": {
            "name": "Get active alerts",
            "description": "Return the generator's active alerts.",
            "fields": {"device_id": DEVICE_FIELD},
        },
        "get_maintenance_history": {
            "name": "Get maintenance history",
            "description": "Return the maintenance notes and schedule.",
            "fields": {"device_id": DEVICE_FIELD},
        },
        "get_notifications": {
            "name": "Get notifications",
            "description": "Return the app notifications for the generator.",
            "fields": {
                "device_id": DEVICE_FIELD,
                "limit": field("Limit", "The most notifications to return, newest first."),
            },
        },
        "get_generator_data": {
            "name": "Get generator data",
            "description": "Return the raw device and details payloads as the service sent them.",
            "fields": {"device_id": DEVICE_FIELD},
        },
        "get_parameter_definitions": {
            "name": "Get parameter definitions",
            "description": "Return the controller's parameter catalogue (names, types, ranges, units).",
            "fields": {
                "device_id": DEVICE_FIELD,
                "kind": field("Controller", "The generator's controller or the transfer switch's."),
            },
        },
    },
}


PLACEHOLDER = re.compile(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}")


def leaves(tree: dict[str, Any], path: tuple[str, ...] = ()) -> Iterator[tuple[str, str]]:
    """Every `(dotted.path, text)` in a translation tree."""
    for key, value in tree.items():
        if isinstance(value, dict):
            yield from leaves(value, (*path, key))
        else:
            yield ".".join((*path, key)), value


def problems_with(source: str, value: Any) -> list[str]:
    """Why `value` cannot stand in for `source` (Home Assistant's rules, plus placeholders)."""
    if not isinstance(value, str) or not value:
        return ["is empty"]
    found = []
    if sorted(PLACEHOLDER.findall(value)) != sorted(PLACEHOLDER.findall(source)):
        found.append(f"placeholders differ from the English ({source!r})")
    if value != value.strip():
        found.append("has leading or trailing whitespace")
    if re.search(r"<[a-zA-Z/][^>]*>", value):
        found.append("contains HTML")
    if re.search(r"'\{[^}]+\}'", value):
        found.append("wraps a placeholder in single quotes")
    return found


def translate(
    tree: dict[str, Any],
    strings: dict[str, str],
    overrides: dict[str, str],
    missing: list[str],
    path: tuple[str, ...] = (),
) -> dict[str, Any]:
    """`tree` with every text that has a translation; texts without one are left out."""
    out: dict[str, Any] = {}
    for key, value in tree.items():
        here = (*path, key)
        if isinstance(value, dict):
            branch = translate(value, strings, overrides, missing, here)
            if branch:
                out[key] = branch
            continue
        dotted = ".".join(here)
        translated = overrides.get(dotted) or strings.get(value)
        if translated:
            out[key] = translated
        else:
            missing.append(dotted)
    return out


def render(tree: dict[str, Any]) -> str:
    return json.dumps(tree, indent=2, ensure_ascii=False) + "\n"


def languages() -> list[str]:
    return sorted(path.stem for path in LOCALES.glob("*.json"))


def build_language(lang: str) -> tuple[dict[str, Any], list[str], list[str]]:
    """The translation tree for `lang`, what is wrong with its catalogue, and what is missing."""
    catalogue = json.loads((LOCALES / f"{lang}.json").read_text(encoding="utf-8"))
    strings: dict[str, str] = catalogue.get("strings", {})
    overrides: dict[str, str] = catalogue.get("overrides", {})
    english = dict(leaves(STRINGS))
    sources = set(english.values())
    problems = [
        f"unexpected top-level key {key!r}" for key in set(catalogue) - {"strings", "overrides"}
    ]
    for source, value in strings.items():
        if source not in sources:
            problems.append(f"strings: {source!r} is not (or no longer) an English text")
            continue
        problems += [f"strings: {source!r} {issue}" for issue in problems_with(source, value)]
    for dotted, value in overrides.items():
        if dotted not in english:
            problems.append(f"overrides: {dotted!r} is not a translation key")
            continue
        problems += [
            f"overrides: {dotted!r} {issue}" for issue in problems_with(english[dotted], value)
        ]
    missing: list[str] = []
    valid = {source: value for source, value in strings.items() if source in sources}
    known = {dotted: value for dotted, value in overrides.items() if dotted in english}
    return translate(STRINGS, valid, known, missing), problems, missing


def check_panel(lang: str) -> tuple[list[str], list[str]]:
    """What is wrong with, and missing from, the panel's locale for `lang`."""
    source: dict[str, str] = json.loads((PANEL_LOCALES / "en.json").read_text(encoding="utf-8"))
    path = PANEL_LOCALES / f"{lang}.json"
    if not path.exists():
        return [f"{path.relative_to(ROOT)} does not exist"], []
    locale: dict[str, str] = json.loads(path.read_text(encoding="utf-8"))
    problems = []
    for key, value in locale.items():
        if key not in source:
            problems.append(f"{key!r} is not (or no longer) a panel message")
            continue
        problems += [f"{key!r} {issue}" for issue in problems_with(source[key], value)]
    return problems, [key for key in source if key not in locale]


def template() -> str:
    """An empty catalogue: every English text once, in the order it first appears."""
    return render({"strings": {text: "" for text in dict.fromkeys(dict(leaves(STRINGS)).values())}})


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument(
        "--check", action="store_true", help="write nothing; fail if a file is stale"
    )
    parser.add_argument(
        "--strict", action="store_true", help="treat a missing translation as an error"
    )
    parser.add_argument("--lang", action="append", help="only this language (repeatable)")
    parser.add_argument("--template", action="store_true", help="print an empty catalogue and exit")
    args = parser.parse_args()
    if args.template:
        sys.stdout.write(template())
        return 0

    failed = False
    outputs: dict[Path, str] = {}
    selected = args.lang or languages()
    if not args.lang:
        # The English is held to the same rules as the translations (they are hassfest's).
        for dotted, text in leaves(STRINGS):
            for issue in problems_with(text, text):
                print(f"error: {dotted}: the English text {issue}")
                failed = True
        english = render(STRINGS)
        outputs[COMPONENT / "strings.json"] = english
        outputs[COMPONENT / "translations" / "en.json"] = english
        for path in (COMPONENT / "translations").glob("*.json"):
            if path.stem != "en" and path.stem not in selected:
                print(f"error: {path.relative_to(ROOT)} has no catalogue in scripts/locales/")
                failed = True
        for path in PANEL_LOCALES.glob("*.json"):
            if path.stem != "en" and path.stem not in selected:
                print(f"error: {path.relative_to(ROOT)} has no catalogue in scripts/locales/")
                failed = True

    total = len(dict(leaves(STRINGS)))
    for lang in selected:
        tree, problems, missing = build_language(lang)
        panel_problems, panel_missing = check_panel(lang)
        outputs[COMPONENT / "translations" / f"{lang}.json"] = render(tree)
        for problem in problems:
            print(f"error: scripts/locales/{lang}.json: {problem}")
        for problem in panel_problems:
            print(f"error: frontend/src/locales/{lang}.json: {problem}")
        failed = failed or bool(problems or panel_problems)
        for label, gaps in (("integration", missing), ("panel", panel_missing)):
            if gaps:
                print(
                    f"{'error' if args.strict else 'note'}: {lang}: {len(gaps)} {label} text(s) untranslated"
                )
                for gap in gaps[:20] if not args.strict else gaps:
                    print(f"    {gap}")
                failed = failed or args.strict
        print(f"{lang}: {total - len(missing)}/{total} integration texts translated")

    for path, text in outputs.items():
        current = path.read_text(encoding="utf-8") if path.exists() else None
        if current == text:
            continue
        if args.check:
            print(f"error: {path.relative_to(ROOT)} is stale; run scripts/build_translations.py")
            failed = True
        else:
            path.parent.mkdir(exist_ok=True)
            path.write_text(text, encoding="utf-8")
            print(f"wrote {path.relative_to(ROOT)}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
