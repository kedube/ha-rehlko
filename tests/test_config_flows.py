"""Drive actual Home Assistant config flows, including account identity checks."""

from unittest.mock import AsyncMock, patch

from homeassistant.config_entries import SOURCE_USER
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.rehlko_energy.config_flow import ValidationResult
from custom_components.rehlko_energy.const import DOMAIN

INPUT = {
    "username": "owner@example.com",
    "password": "pw",
    "app_credentials": {
        "client_id": "client",
        "client_secret": "secret",
        "api_key": "key",
    },
}
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


STORED = {
    "username": "owner@example.com",
    "password": "old-password",
    "client_id": "client",
    "client_secret": "stored-secret",
    "api_key": "stored-key",
    "refresh_token": "stored-refresh",
}


async def test_reconfigure_never_sends_stored_secrets_and_keeps_blank_ones(
    hass, enable_custom_integrations
):
    entry = MockConfigEntry(domain=DOMAIN, unique_id="owner", data=STORED)
    entry.add_to_hass(hass)
    form = await entry.start_reconfigure_flow(hass)
    assert form["type"] is FlowResultType.FORM
    # The form the browser receives names the client ID and nothing secret.
    import voluptuous_serialize
    from homeassistant.helpers import config_validation as cv

    shown = repr(
        voluptuous_serialize.convert(form["data_schema"], custom_serializer=cv.custom_serializer)
    )
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
