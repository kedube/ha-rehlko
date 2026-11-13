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
from .app_credentials import (
    STORED_KEYS,
    app_credentials_for,
    builtin_app_credentials,
    stored_app_credentials,
    without_app_credentials,
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
# Errors that are about the app's credentials, not the account's.
APP_CREDENTIAL_ERRORS = frozenset({"invalid_app_credentials", "invalid_api_key"})


def _app_fields(
    client_id: str | None = None, *, required: bool = True
) -> dict[vol.Marker, TextSelector]:
    """The three app-credential fields.

    Only a client ID is ever filled in for the user. A saved secret and API key stay on the
    server: they are never sent back to the browser.
    """
    marker = vol.Required if required else vol.Optional
    shown = {"suggested_value": client_id} if client_id else None
    return {
        marker(CONF_CLIENT_ID, description=shown): TextSelector(),
        marker(CONF_CLIENT_SECRET): _PASSWORD,
        marker(CONF_API_KEY): _PASSWORD,
    }


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
    typed: Mapping[str, str], stored: Mapping[str, Any] | None = None
) -> AppCredentials:
    """The app credentials as typed, without the quotes the app's `.env` wraps them in.

    A field left empty keeps the value from `stored` (the entry being reconfigured), and is an
    empty string if there is none.
    """

    def clean(key: str) -> str:
        value = (typed.get(key) or "").strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
            value = value[1:-1].strip()
        return value or str((stored or {}).get(key) or "")

    return AppCredentials(clean(CONF_CLIENT_ID), clean(CONF_CLIENT_SECRET), clean(CONF_API_KEY))


def _complete(app: AppCredentials) -> bool:
    return bool(app.client_id and app.client_secret and app.api_key)


def _as_data(app: AppCredentials) -> dict[str, str]:
    return dict(zip(STORED_KEYS, (app.client_id, app.client_secret, app.api_key), strict=True))


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

    def __init__(self) -> None:
        # The account typed on the sign-in form, kept while the app credentials are asked for,
        # and a set of app credentials entered by hand that the sign-in service accepted.
        self._login: dict[str, str] = {}
        self._app: AppCredentials | None = None

    async def _async_create(self, result: ValidationResult) -> ConfigFlowResult:
        await self.async_set_unique_id(result.account_id)
        self._abort_if_unique_id_configured()
        return self.async_create_entry(
            title=self._login[CONF_USERNAME],
            data={
                **self._login,
                # Only a set entered by hand is saved; the built-in one is read when needed.
                **(_as_data(self._app) if self._app else {}),
                CONF_REFRESH_TOKEN: result.refresh_token,
                CONF_BASE_URL: result.base_url,
                CONF_ACCOUNT_ID: result.account_id,
            },
        )

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            self._login = {
                CONF_USERNAME: user_input[CONF_USERNAME].strip(),
                CONF_PASSWORD: user_input[CONF_PASSWORD],
            }
            app = self._app or builtin_app_credentials()
            result = await self._async_try(
                self._login[CONF_USERNAME], self._login[CONF_PASSWORD], app, errors
            )
            if result is not None:
                return await self._async_create(result)
            if errors["base"] in APP_CREDENTIAL_ERRORS:
                # Rehlko no longer accepts this set: ask for the app's current one.
                self._app = None
                return await self.async_step_app_credentials()
        return self.async_show_form(
            step_id="user", data_schema=_user_schema(user_input), errors=errors
        )

    async def async_step_app_credentials(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask for the app's credentials: Rehlko refused the built-in ones."""
        errors: dict[str, str] = {}
        if user_input is not None:
            app = _app_credentials(user_input)
            result = await self._async_try(
                self._login[CONF_USERNAME], self._login[CONF_PASSWORD], app, errors
            )
            if result is not None:
                self._app = app
                return await self._async_create(result)
            if errors["base"] in ("invalid_auth", "sign_in_denied"):
                # The service accepted the app and refused the account: back to the sign-in
                # form, keeping what was typed here.
                self._app = app
                return self.async_show_form(
                    step_id="user", data_schema=_user_schema(self._login), errors=errors
                )
        return self.async_show_form(
            step_id="app_credentials", data_schema=vol.Schema(_app_fields()), errors=errors
        )

    async def async_step_reauth(self, entry_data: Mapping[str, Any]) -> ConfigFlowResult:
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        entry = self._get_reauth_entry()
        errors: dict[str, str] = {}
        if user_input is not None:
            result = await self._async_try(
                entry.data[CONF_USERNAME],
                user_input[CONF_PASSWORD],
                app_credentials_for(entry.data),
                errors,
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
        """Change the password, or enter app credentials of the entry's own.

        The app-credential fields are for the day the built-in set stops working. Typing in
        any of them gives the entry its own set, completed from the one it already has;
        leaving all three empty goes back to the built-in set.
        """
        entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}
        builtin = builtin_app_credentials()
        saved = stored_app_credentials(entry.data)
        if user_input is not None:
            typed = user_input.get(SECTION_APP_CREDENTIALS) or {}
            own = None
            if any((typed.get(key) or "").strip() for key in STORED_KEYS):
                own = _app_credentials(typed, entry.data if saved else None)
            app = own or builtin
            result = None
            if not _complete(app):
                errors["base"] = "incomplete_app_credentials"
            else:
                result = await self._async_try(
                    entry.data[CONF_USERNAME], user_input[CONF_PASSWORD], app, errors
                )
            if result is not None:
                await self.async_set_unique_id(result.account_id)
                self._abort_if_unique_id_mismatch(reason="wrong_account")
                return self.async_update_reload_and_abort(
                    entry,
                    data={
                        **without_app_credentials(entry.data),
                        # A copy of the built-in set is not worth saving.
                        **(_as_data(own) if own and own != builtin else {}),
                        CONF_PASSWORD: user_input[CONF_PASSWORD],
                        CONF_REFRESH_TOKEN: result.refresh_token,
                        CONF_BASE_URL: result.base_url,
                    },
                )
        # The section is open only when the entry has a set of its own. That set's client ID is
        # filled in, so it can be seen, changed or cleared.
        fields = _app_fields(saved.client_id if saved else None, required=False)
        schema = vol.Schema(
            {
                vol.Required(CONF_PASSWORD): _PASSWORD,
                vol.Required(SECTION_APP_CREDENTIALS): section(
                    vol.Schema(fields), {"collapsed": saved is None}
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
