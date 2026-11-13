"""The Energy Mgmt. app's own credentials: its OAuth client and its API key.

They identify the app, not an account, and every copy of the app carries the same ones (in its
`flutter_assets/.env`). Home Assistant's built-in Rehlko integration signs in with them too:
its library, aiokem, publishes the same values. They are written out here so that setting the
integration up takes an email and a password and nothing else.

If Rehlko changes them, signing in fails with an app-credentials error. Setup then asks for
the current ones, and Reconfigure has a section for them. A set entered by hand is saved with
the config entry and takes precedence over this one, until a release brings this one up to
date.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Final

from .api import AppCredentials
from .const import CONF_API_KEY, CONF_CLIENT_ID, CONF_CLIENT_SECRET

# CLIENT_ID, CLIENT_SECRET and API_KEY in the app's `.env`.
BUILTIN: Final = AppCredentials(
    client_id="0oa1qicpdagKiwEzF1d8",
    client_secret="wtZkQp6V5OOo1oOr8eHRGNqAXF7k6IixmXhH4vcru6Ml1JtKPNhmwl0Cu0igBEHF",
    api_key="pgH7QzFHJx4w46fI~5Uzi4RvtTwlEXp",
)

STORED_KEYS = (CONF_CLIENT_ID, CONF_CLIENT_SECRET, CONF_API_KEY)


def builtin_app_credentials() -> AppCredentials:
    """The set written into the integration."""
    return BUILTIN


def stored_app_credentials(data: Mapping[str, Any]) -> AppCredentials | None:
    """The set saved with a config entry, if it has a complete one of its own."""
    if all(data.get(key) for key in STORED_KEYS):
        return AppCredentials(*(str(data[key]) for key in STORED_KEYS))
    return None


def without_app_credentials(data: Mapping[str, Any]) -> dict[str, Any]:
    """`data` without a saved set, for an entry that uses the built-in one."""
    return {key: value for key, value in data.items() if key not in STORED_KEYS}


def app_credentials_for(data: Mapping[str, Any]) -> AppCredentials:
    """What an entry signs in with: its own set if it has one, otherwise the built-in one."""
    return stored_app_credentials(data) or builtin_app_credentials()
