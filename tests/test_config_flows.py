"""Drive actual Home Assistant config flows, including account identity checks."""

import json
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant.config_entries import SOURCE_USER
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.rehlko_energy.api import (
    AppCredentials,
    RehlkoAppCredentialsError,
    RehlkoAuthError,
)
from custom_components.rehlko_energy.config_flow import ValidationResult
from custom_components.rehlko_energy.const import DOMAIN
from custom_components.rehlko_energy.sidebar import async_setup_sidebar

INPUT = {"username": "owner@example.com", "password": "pw"}
TYPED_APP = {"client_id": "client", "client_secret": "secret", "api_key": "key"}
APP_KEYS = set(TYPED_APP)
VALIDATE = "custom_components.rehlko_energy.config_flow.async_validate"
RESULT = ValidationResult(
    base_url="https://api.example", refresh_token="refresh", account_id="owner", generators=1
)


async def test_user_flow_creates_validated_unique_account(hass, enable_custom_integrations):
    with (
        patch("custom_components.rehlko_energy.config_flow.async_validate", return_value=RESULT),
        patch(
            "custom_components.rehlko_energy.async_setup_entry",
            new_callable=AsyncMock,
            return_value=True,
        ),
    ):
        form = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
        assert form["type"] is FlowResultType.FORM
        created = await hass.config_entries.flow.async_configure(form["flow_id"], INPUT)
        assert created["type"] is FlowResultType.CREATE_ENTRY
        assert created["result"].unique_id == "owner"
        assert created["data"]["refresh_token"] == "refresh"
        await hass.async_block_till_done()


async def test_setup_asks_only_for_the_account(hass, enable_custom_integrations, builtin_app):
    """The app's own credentials are built in, and are not copied into the entry."""
    with (
        patch(VALIDATE, return_value=RESULT) as validate,
        patch("custom_components.rehlko_energy.async_setup_entry", return_value=True),
    ):
        form = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
        assert set(form["data_schema"].schema) == {"username", "password"}
        created = await hass.config_entries.flow.async_configure(form["flow_id"], INPUT)
        await hass.async_block_till_done()
    assert created["type"] is FlowResultType.CREATE_ENTRY
    assert APP_KEYS.isdisjoint(created["data"])
    assert validate.call_args.args[3] == builtin_app


@pytest.mark.parametrize(
    "refusal",
    [RehlkoAppCredentialsError("invalid_client"), RehlkoAuthError("no", reason="unauthorized")],
    ids=["client-refused", "api-key-refused"],
)
async def test_setup_asks_for_app_credentials_when_the_built_in_ones_are_refused(
    hass, enable_custom_integrations, refusal
):
    with (
        patch(VALIDATE, side_effect=[refusal, RESULT]) as validate,
        patch("custom_components.rehlko_energy.async_setup_entry", return_value=True),
    ):
        form = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}, data=INPUT
        )
        assert (form["type"], form["step_id"]) == (FlowResultType.FORM, "app_credentials")
        created = await hass.config_entries.flow.async_configure(form["flow_id"], TYPED_APP)
        await hass.async_block_till_done()
    assert created["type"] is FlowResultType.CREATE_ENTRY
    assert validate.call_args.args[3] == AppCredentials("client", "secret", "key")
    assert {key: created["data"][key] for key in APP_KEYS} == TYPED_APP


async def test_a_wrong_password_found_after_typing_app_credentials_keeps_them(
    hass, enable_custom_integrations
):
    refused = RehlkoAppCredentialsError("invalid_client")
    wrong_password = RehlkoAuthError("denied", reason="invalid_grant")
    with (
        patch(VALIDATE, side_effect=[refused, wrong_password, RESULT]) as validate,
        patch("custom_components.rehlko_energy.async_setup_entry", return_value=True),
    ):
        form = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}, data=INPUT
        )
        # The service accepted the app and refused the account: the sign-in form comes back.
        form = await hass.config_entries.flow.async_configure(form["flow_id"], TYPED_APP)
        assert (form["step_id"], form["errors"]) == ("user", {"base": "invalid_auth"})
        created = await hass.config_entries.flow.async_configure(
            form["flow_id"], {**INPUT, "password": "right"}
        )
        await hass.async_block_till_done()
    assert created["type"] is FlowResultType.CREATE_ENTRY
    assert created["data"]["password"] == "right"
    assert validate.call_args.args[3] == AppCredentials("client", "secret", "key")
    assert {key: created["data"][key] for key in APP_KEYS} == TYPED_APP


async def test_duplicate_account_aborts(hass, enable_custom_integrations):
    entry = MockConfigEntry(domain=DOMAIN, unique_id="owner", data={})
    entry.add_to_hass(hass)
    with patch("custom_components.rehlko_energy.config_flow.async_validate", return_value=RESULT):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}, data=INPUT
        )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_reauth_rejects_another_cloud_account(hass, enable_custom_integrations):
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="original",
        data={
            "username": "owner@example.com",
            "client_id": "client",
            "client_secret": "secret",
            "api_key": "key",
        },
    )
    entry.add_to_hass(hass)
    form = await entry.start_reauth_flow(hass)
    with patch("custom_components.rehlko_energy.config_flow.async_validate", return_value=RESULT):
        result = await hass.config_entries.flow.async_configure(
            form["flow_id"], {"password": "new"}
        )
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "wrong_account"


async def test_reauth_uses_the_built_in_app_credentials(
    hass, enable_custom_integrations, builtin_app
):
    entry = MockConfigEntry(
        domain=DOMAIN, unique_id="owner", data={"username": "owner@example.com"}
    )
    entry.add_to_hass(hass)
    form = await entry.start_reauth_flow(hass)
    with (
        patch(VALIDATE, return_value=RESULT) as validate,
        patch("custom_components.rehlko_energy.async_setup_entry", return_value=True),
    ):
        done = await hass.config_entries.flow.async_configure(form["flow_id"], {"password": "new"})
        await hass.async_block_till_done()
    assert (done["type"], done["reason"]) == (FlowResultType.ABORT, "reauth_successful")
    assert validate.call_args.args[3] == builtin_app
    assert entry.data["password"] == "new"


STORED = {
    "username": "owner@example.com",
    "password": "old-password",
    "client_id": "client",
    "client_secret": "stored-secret",
    "api_key": "stored-key",
    "refresh_token": "stored-refresh",
}


async def test_reconfigure_never_sends_stored_secrets_and_keeps_blank_ones(
    hass, enable_custom_integrations, hass_client
):
    entry = MockConfigEntry(domain=DOMAIN, unique_id="owner", data=STORED)
    entry.add_to_hass(hass)
    # Start the flow as the browser does, and read exactly what Home Assistant sends it: the
    # form names the client ID and nothing secret.
    # Everything that adds web routes is in place before the test's HTTP client starts the
    # server; the integration's own route is the panel's bundle.
    for component in ("config", "panel_custom"):
        assert await async_setup_component(hass, component, {})
    await async_setup_sidebar(hass)
    http = await hass_client()
    response = await http.post(
        "/api/config/config_entries/flow", json={"handler": DOMAIN, "entry_id": entry.entry_id}
    )
    assert response.status == 200
    shown = await response.text()
    form = json.loads(shown)
    assert (form["type"], form["step_id"]) == ("form", "reconfigure")
    assert "client" in shown
    for secret in ("stored-secret", "stored-key", "stored-refresh", "old-password"):
        assert secret not in shown

    with (
        patch(
            "custom_components.rehlko_energy.config_flow.async_validate", return_value=RESULT
        ) as validate,
        patch("custom_components.rehlko_energy.async_setup_entry", return_value=True),
    ):
        result = await hass.config_entries.flow.async_configure(
            form["flow_id"],
            {"password": "new-password", "app_credentials": {"client_id": "client"}},
        )
        await hass.async_block_till_done()
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    app = validate.call_args.args[3]
    assert (app.client_id, app.client_secret, app.api_key) == (
        "client",
        "stored-secret",
        "stored-key",
    )
    assert entry.data["client_secret"] == "stored-secret"
    assert entry.data["api_key"] == "stored-key"
    assert entry.data["password"] == "new-password"


async def test_reconfigure_replaces_secrets_that_are_typed(hass, enable_custom_integrations):
    entry = MockConfigEntry(domain=DOMAIN, unique_id="owner", data=STORED)
    entry.add_to_hass(hass)
    form = await entry.start_reconfigure_flow(hass)
    with (
        patch("custom_components.rehlko_energy.config_flow.async_validate", return_value=RESULT),
        patch("custom_components.rehlko_energy.async_setup_entry", return_value=True),
    ):
        await hass.config_entries.flow.async_configure(
            form["flow_id"],
            {
                "password": "new-password",
                "app_credentials": {
                    "client_id": "client-2",
                    "client_secret": "'rotated-secret'",
                    "api_key": "rotated-key",
                },
            },
        )
        await hass.async_block_till_done()
    assert entry.data["client_id"] == "client-2"
    assert entry.data["client_secret"] == "rotated-secret"
    assert entry.data["api_key"] == "rotated-key"


async def _reconfigure(hass, entry, section, validate=None):
    form = await entry.start_reconfigure_flow(hass)
    with (
        patch(VALIDATE, return_value=RESULT) as validated,
        patch("custom_components.rehlko_energy.async_setup_entry", return_value=True),
    ):
        result = await hass.config_entries.flow.async_configure(
            form["flow_id"], {"password": "new-password", "app_credentials": section}
        )
        await hass.async_block_till_done()
    return form, result, validated


async def test_reconfigure_with_empty_fields_goes_back_to_the_built_in_set(
    hass, enable_custom_integrations, builtin_app
):
    entry = MockConfigEntry(domain=DOMAIN, unique_id="owner", data=STORED)
    entry.add_to_hass(hass)
    form, result, validated = await _reconfigure(hass, entry, {})
    # A saved set keeps the section open; clearing its fields drops the set.
    assert form["data_schema"].schema["app_credentials"].options == {"collapsed": False}
    assert result["reason"] == "reconfigure_successful"
    assert validated.call_args.args[3] == builtin_app
    assert APP_KEYS.isdisjoint(entry.data)
    assert entry.data["password"] == "new-password"
    assert entry.data["username"] == "owner@example.com"


async def test_reconfigure_hides_the_section_when_the_built_in_set_is_in_use(
    hass, enable_custom_integrations, builtin_app
):
    data = {key: value for key, value in STORED.items() if key not in APP_KEYS}
    entry = MockConfigEntry(domain=DOMAIN, unique_id="owner", data=data)
    entry.add_to_hass(hass)
    form, result, validated = await _reconfigure(hass, entry, {})
    assert form["data_schema"].schema["app_credentials"].options == {"collapsed": True}
    assert result["reason"] == "reconfigure_successful"
    assert validated.call_args.args[3] == builtin_app
    assert APP_KEYS.isdisjoint(entry.data)


async def test_reconfigure_wants_all_three_app_credentials_or_none(
    hass, enable_custom_integrations
):
    data = {key: value for key, value in STORED.items() if key not in APP_KEYS}
    entry = MockConfigEntry(domain=DOMAIN, unique_id="owner", data=data)
    entry.add_to_hass(hass)
    _form, result, validated = await _reconfigure(hass, entry, {"client_id": "only-this"})
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "incomplete_app_credentials"}
    validated.assert_not_called()
    assert entry.data == data


async def test_reconfigure_does_not_save_a_copy_of_the_built_in_set(
    hass, enable_custom_integrations, builtin_app
):
    entry = MockConfigEntry(domain=DOMAIN, unique_id="owner", data=STORED)
    entry.add_to_hass(hass)
    typed = {
        "client_id": builtin_app.client_id,
        "client_secret": builtin_app.client_secret,
        "api_key": builtin_app.api_key,
    }
    _form, result, _validated = await _reconfigure(hass, entry, typed)
    assert result["reason"] == "reconfigure_successful"
    assert APP_KEYS.isdisjoint(entry.data)


async def test_a_refused_password_sign_in_is_not_reported_as_a_wrong_password(
    hass, enable_custom_integrations
):
    from custom_components.rehlko_energy.api import RehlkoAuthError

    for reason, expected in (
        ("mfa_required", "sign_in_denied"),
        ("access_denied", "sign_in_denied"),
        ("invalid_grant", "invalid_auth"),
    ):
        with patch(
            "custom_components.rehlko_energy.config_flow.async_validate",
            side_effect=RehlkoAuthError("denied", reason=reason),
        ):
            result = await hass.config_entries.flow.async_init(
                DOMAIN, context={"source": SOURCE_USER}, data=INPUT
            )
        assert result["type"] is FlowResultType.FORM
        assert result["errors"] == {"base": expected}, reason
