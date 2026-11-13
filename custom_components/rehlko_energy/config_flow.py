"""Config flow: sign in with the Rehlko / Kohler Energy Management account."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import section
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    BooleanSelector,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .api import (
    AppCredentials,
    OktaAuth,
    RehlkoApiError,
    RehlkoAppCredentialsError,
    RehlkoAuthError,
    RehlkoClient,
    RehlkoConnectionError,
    RehlkoError,
)
from .const import (
    API_BASE_URLS,
    CONF_ACCOUNT_ID,
    CONF_ACTIVE_SCAN_INTERVAL,
    CONF_API_KEY,
    CONF_BASE_URL,
    CONF_CLIENT_ID,
    CONF_CLIENT_SECRET,
    CONF_EXTRA_DIAGNOSTICS,
    CONF_FEED_INTERVAL,
    CONF_NOTIFICATION_LIMIT,
    CONF_REFRESH_TOKEN,
    CONF_SCAN_INTERVAL,
    CONF_SIDEBAR_PANEL,
    DEFAULT_ACTIVE_SCAN_INTERVAL,
    DEFAULT_EXTRA_DIAGNOSTICS,
    DEFAULT_FEED_INTERVAL,
    DEFAULT_NOTIFICATION_LIMIT,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_SIDEBAR_PANEL,
    DOMAIN,
    MAX_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
    OKTA_SCOPES,
    OKTA_TOKEN_URL,
    SECTION_APP_CREDENTIALS,
)

_LOGGER = logging.getLogger(__name__)

_PASSWORD = TextSelector(TextSelectorConfig(type=TextSelectorType.PASSWORD))
SIGN_IN_DENIED = frozenset({"mfa_required", "access_denied", "interaction_required"})


def _app_section(
    defaults: Mapping[str, Any] | None = None, *, collapsed: bool = False, stored: bool = False
) -> section:
    """The app-credentials section.

    With `stored`, the entry already holds a secret and an API key: those two fields may be
    left empty to keep them, and the stored values are never sent back to the browser.
    """
    d = defaults or {}
    secret = vol.Optional if stored else vol.Required
    return section(
        vol.Schema(
            {
                vol.Required(
                    CONF_CLIENT_ID, default=d.get(CONF_CLIENT_ID, vol.UNDEFINED)
                ): TextSelector(),
                secret(
                    CONF_CLIENT_SECRET, default=d.get(CONF_CLIENT_SECRET, vol.UNDEFINED)
                ): _PASSWORD,
                secret(CONF_API_KEY, default=d.get(CONF_API_KEY, vol.UNDEFINED)): _PASSWORD,
            }
        ),
        {"collapsed": collapsed},
    )


def _user_schema(defaults: Mapping[str, Any] | None = None) -> vol.Schema:
    d = defaults or {}
    return vol.Schema(
        {
            vol.Required(CONF_USERNAME, default=d.get(CONF_USERNAME, vol.UNDEFINED)): TextSelector(
                TextSelectorConfig(type=TextSelectorType.EMAIL, autocomplete="username")
            ),
            vol.Required(CONF_PASSWORD): TextSelector(
                TextSelectorConfig(type=TextSelectorType.PASSWORD, autocomplete="current-password")
            ),
            vol.Required(SECTION_APP_CREDENTIALS): _app_section(d.get(SECTION_APP_CREDENTIALS)),
        }
    )


class ValidationResult:
    def __init__(
        self, *, base_url: str, refresh_token: str | None, account_id: str, generators: int
    ) -> None:
        self.base_url = base_url
        self.refresh_token = refresh_token
        self.account_id = account_id
        self.generators = generators


async def async_validate(
    hass: HomeAssistant, username: str, password: str, app: AppCredentials
) -> ValidationResult:
    """Sign in, find a host that answers, and count the account's generators."""
    session = async_get_clientsession(hass)
    auth = OktaAuth(
        session,
        app,
        token_url=OKTA_TOKEN_URL,
        scopes=OKTA_SCOPES,
        username=username,
        password=password,
    )
    tokens = await auth.async_login()
    last_error: RehlkoError | None = None
    for base_url in API_BASE_URLS:
        client = RehlkoClient(session, auth, base_url=base_url)
        try:
            homes = await client.get_homes()
            me = await client.get_me()
        except RehlkoConnectionError as err:
            last_error = err
            continue
        account_id = str(me.get("id") or tokens.claims.get("sub") or username.strip().lower())
        count = sum(len(h.get("devices") or []) for h in homes)
        return ValidationResult(
            base_url=base_url,
            refresh_token=auth.refresh_token,
            account_id=account_id,
            generators=count,
        )
    assert last_error is not None
    raise last_error


def _app_credentials(
    section_input: Mapping[str, str], stored: Mapping[str, Any] | None = None
) -> AppCredentials:
    """The app credentials as typed, without the quotes the app's `.env` wraps them in.

    A field left empty keeps the value from `stored` (the entry being reconfigured).
    """

    def clean(key: str) -> str:
        value = (section_input.get(key) or "").strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
            value = value[1:-1].strip()
        return value or str((stored or {}).get(key) or "")

    return AppCredentials(clean(CONF_CLIENT_ID), clean(CONF_CLIENT_SECRET), clean(CONF_API_KEY))


def _error_key(err: Exception) -> str:
    if isinstance(err, RehlkoAppCredentialsError):
        return "invalid_app_credentials"
    if isinstance(err, RehlkoAuthError):
        if err.reason == "unauthorized":
            return "invalid_api_key"
        # Okta answers a password sign-in this way when the account's policy wants more than
        # a password (multi-factor), which is not the same as a wrong password.
        return "sign_in_denied" if err.reason in SIGN_IN_DENIED else "invalid_auth"
    if isinstance(err, RehlkoApiError) and err.status in (401, 403):
        return "invalid_api_key"
    if isinstance(err, RehlkoConnectionError):
        return "cannot_connect"
    return "unknown"


class RehlkoConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Rehlko Energy Management."""

    VERSION = 1
    MINOR_VERSION = 2  # 2: entity unique IDs carry the account (see async_migrate_entry)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return RehlkoOptionsFlow()

    async def _async_try(
        self, username: str, password: str, app: AppCredentials, errors: dict[str, str]
    ) -> ValidationResult | None:
        try:
            result = await async_validate(self.hass, username, password, app)
        except RehlkoError as err:
            errors["base"] = _error_key(err)
            return None
        except Exception:
            _LOGGER.exception("Unexpected error validating the Rehlko account")
            errors["base"] = "unknown"
            return None
        if result.generators == 0:
            errors["base"] = "no_generators"
            return None
        return result

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            username = user_input[CONF_USERNAME].strip()
            app = _app_credentials(user_input[SECTION_APP_CREDENTIALS])
            result = await self._async_try(username, user_input[CONF_PASSWORD], app, errors)
            if result is not None:
                await self.async_set_unique_id(result.account_id)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=username,
                    data={
                        CONF_USERNAME: username,
                        CONF_PASSWORD: user_input[CONF_PASSWORD],
                        CONF_CLIENT_ID: app.client_id,
                        CONF_CLIENT_SECRET: app.client_secret,
                        CONF_API_KEY: app.api_key,
                        CONF_REFRESH_TOKEN: result.refresh_token,
                        CONF_BASE_URL: result.base_url,
                        CONF_ACCOUNT_ID: result.account_id,
                    },
                )
        return self.async_show_form(
            step_id="user", data_schema=_user_schema(user_input), errors=errors
        )

    async def async_step_reauth(self, entry_data: Mapping[str, Any]) -> ConfigFlowResult:
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        entry = self._get_reauth_entry()
        errors: dict[str, str] = {}
        if user_input is not None:
            app = AppCredentials(
                entry.data[CONF_CLIENT_ID], entry.data[CONF_CLIENT_SECRET], entry.data[CONF_API_KEY]
            )
            result = await self._async_try(
                entry.data[CONF_USERNAME], user_input[CONF_PASSWORD], app, errors
            )
            if result is not None:
                await self.async_set_unique_id(result.account_id)
                self._abort_if_unique_id_mismatch(reason="wrong_account")
                return self.async_update_reload_and_abort(
                    entry,
                    data_updates={
                        CONF_PASSWORD: user_input[CONF_PASSWORD],
                        CONF_REFRESH_TOKEN: result.refresh_token,
                        CONF_BASE_URL: result.base_url,
                    },
                )
        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema({vol.Required(CONF_PASSWORD): _PASSWORD}),
            description_placeholders={"username": entry.data[CONF_USERNAME]},
            errors=errors,
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Change the password or the app credentials (for example after an app update)."""
        entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}
        if user_input is not None:
            app = _app_credentials(user_input[SECTION_APP_CREDENTIALS], entry.data)
            result = await self._async_try(
                entry.data[CONF_USERNAME], user_input[CONF_PASSWORD], app, errors
            )
            if result is not None:
                await self.async_set_unique_id(result.account_id)
                self._abort_if_unique_id_mismatch(reason="wrong_account")
                return self.async_update_reload_and_abort(
                    entry,
                    data_updates={
                        CONF_PASSWORD: user_input[CONF_PASSWORD],
                        CONF_CLIENT_ID: app.client_id,
                        CONF_CLIENT_SECRET: app.client_secret,
                        CONF_API_KEY: app.api_key,
                        CONF_REFRESH_TOKEN: result.refresh_token,
                        CONF_BASE_URL: result.base_url,
                    },
                )
        # Only the client ID is shown. The stored secret and API key stay on the server:
        # leaving those fields empty keeps them.
        schema = vol.Schema(
            {
                vol.Required(CONF_PASSWORD): _PASSWORD,
                vol.Required(SECTION_APP_CREDENTIALS): _app_section(
                    {CONF_CLIENT_ID: entry.data.get(CONF_CLIENT_ID)}, stored=True
                ),
            }
        )
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=schema,
            description_placeholders={"username": entry.data[CONF_USERNAME]},
            errors=errors,
        )


def _seconds(minimum: int, maximum: int, step: int = 5) -> NumberSelector:
    return NumberSelector(
        NumberSelectorConfig(
            min=minimum,
            max=maximum,
            step=step,
            mode=NumberSelectorMode.BOX,
            unit_of_measurement="s",
        )
    )


class RehlkoOptionsFlow(OptionsFlow):
    """Polling cadence, the sidebar panel, and the catch-all diagnostic entities."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            cleaned = {k: int(v) if isinstance(v, float) else v for k, v in user_input.items()}
            return self.async_create_entry(data=cleaned)
        o = self.config_entry.options
        schema = vol.Schema(
            {
                vol.Required(
                    CONF_SCAN_INTERVAL, default=o.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
                ): _seconds(MIN_SCAN_INTERVAL, MAX_SCAN_INTERVAL),
                vol.Required(
                    CONF_ACTIVE_SCAN_INTERVAL,
                    default=o.get(CONF_ACTIVE_SCAN_INTERVAL, DEFAULT_ACTIVE_SCAN_INTERVAL),
                ): _seconds(MIN_SCAN_INTERVAL, MAX_SCAN_INTERVAL),
                vol.Required(
                    CONF_FEED_INTERVAL, default=o.get(CONF_FEED_INTERVAL, DEFAULT_FEED_INTERVAL)
                ): _seconds(30, 3600),
                vol.Required(
                    CONF_NOTIFICATION_LIMIT,
                    default=o.get(CONF_NOTIFICATION_LIMIT, DEFAULT_NOTIFICATION_LIMIT),
                ): NumberSelector(
                    NumberSelectorConfig(min=10, max=200, step=10, mode=NumberSelectorMode.BOX)
                ),
                vol.Required(
                    CONF_SIDEBAR_PANEL, default=o.get(CONF_SIDEBAR_PANEL, DEFAULT_SIDEBAR_PANEL)
                ): BooleanSelector(),
                vol.Required(
                    CONF_EXTRA_DIAGNOSTICS,
                    default=o.get(CONF_EXTRA_DIAGNOSTICS, DEFAULT_EXTRA_DIAGNOSTICS),
                ): BooleanSelector(),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
