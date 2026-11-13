"""Constants for the Rehlko Energy Management integration."""

from __future__ import annotations

from datetime import timedelta
from typing import Final

DOMAIN: Final = "rehlko_energy"
NAME: Final = "Rehlko Energy Management"
MANUFACTURER: Final = "Rehlko (formerly Kohler Energy)"

# --- Identity provider ----------------------------------------------------------------
# The Energy Mgmt. app (com.kohlerpower.homeownerApp) signs in against this Okta
# authorization server. The app's OAuth client ID, client secret and API key are not
# shipped with this integration: the user supplies them during setup (docs/API.md explains
# where the installed app keeps its configuration).
OKTA_ISSUER: Final = "https://auth.home.kohlergenerators.com/oauth2/default"
OKTA_TOKEN_URL: Final = f"{OKTA_ISSUER}/v1/token"
OKTA_SCOPES: Final = "openid profile offline_access email"

# The app's .env names two hosts serving the same `/kem/api/v3` surface; a remote-config
# flag (`useRehlkoUrl`) picks one. The first is what current builds use.
API_BASE_URL: Final = "https://api.hems.rehlko.com"
API_ALT_BASE_URL: Final = "https://api.rk-prod.energymanagement.dev"
API_BASE_URLS: Final = (API_BASE_URL, API_ALT_BASE_URL)

# --- Config entry keys ----------------------------------------------------------------
CONF_REFRESH_TOKEN: Final = "refresh_token"
CONF_ACCOUNT_ID: Final = "account_id"
CONF_BASE_URL: Final = "base_url"
CONF_CLIENT_ID: Final = "client_id"
CONF_CLIENT_SECRET: Final = "client_secret"
CONF_API_KEY: Final = "api_key"
SECTION_APP_CREDENTIALS: Final = "app_credentials"

# --- Options --------------------------------------------------------------------------
CONF_SCAN_INTERVAL: Final = "scan_interval"
CONF_ACTIVE_SCAN_INTERVAL: Final = "active_scan_interval"
CONF_FEED_INTERVAL: Final = "feed_interval"
CONF_SIDEBAR_PANEL: Final = "sidebar_panel"
CONF_EXTRA_DIAGNOSTICS: Final = "extra_diagnostic_entities"
CONF_NOTIFICATION_LIMIT: Final = "notification_limit"

DEFAULT_SCAN_INTERVAL: Final = 60  # seconds, generator in standby
DEFAULT_ACTIVE_SCAN_INTERVAL: Final = 15  # seconds, running / exercising / on generator power
DEFAULT_FEED_INTERVAL: Final = 120  # seconds, activity log / alerts / notifications
DEFAULT_SIDEBAR_PANEL: Final = True
DEFAULT_EXTRA_DIAGNOSTICS: Final = True
DEFAULT_NOTIFICATION_LIMIT: Final = 50

MIN_SCAN_INTERVAL: Final = 10
MAX_SCAN_INTERVAL: Final = 900

# Slow-changing data (maintenance notes, notification settings, profile, cell plan).
SLOW_REFRESH: Final = timedelta(minutes=15)

# --- Events fired on the Home Assistant bus -------------------------------------------
EVENT_DEVICE_EVENT: Final = f"{DOMAIN}_device_event"  # new activity-log entry
EVENT_ALERT: Final = f"{DOMAIN}_alert"  # new active alert
EVENT_ALERT_CLEARED: Final = f"{DOMAIN}_alert_cleared"
EVENT_NOTIFICATION: Final = f"{DOMAIN}_notification"  # new app notification
EVENT_POWER: Final = f"{DOMAIN}_power"  # derived: outage, restore, start, stop

# --- Storage --------------------------------------------------------------------------
STORAGE_VERSION: Final = 1
STORAGE_KEY_SEEN: Final = f"{DOMAIN}.seen"

# --- Exercise -------------------------------------------------------------------------
# Wire values the app offers when scheduling or starting an exercise (the API's "None"
# means no schedule).
EXERCISE_MODES: Final = ("Unloaded", "UnloadedFullSpeed", "LoadedFullSpeed", "EcoExercise")
EXERCISE_FREQUENCIES: Final = ("Weekly", "EveryOtherWeek", "Monthly")
EXERCISE_MIN_MINUTES: Final = 5
EXERCISE_MAX_MINUTES: Final = 60
EXERCISE_DEFAULT_MINUTES: Final = 20

# Utility voltage below this fraction of the generator's nominal output counts as an
# outage when the device does not report a power source.
UTILITY_PRESENT_FRACTION: Final = 0.5
DEFAULT_NOMINAL_VOLTAGE: Final = 240.0
