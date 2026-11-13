"""Credentials stay where they are stored: not in logs, error text, diagnostics or the panel."""

from __future__ import annotations

import json
import logging
from copy import deepcopy
from unittest.mock import AsyncMock, MagicMock, patch

import aiohttp
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.rehlko_energy.api import AppCredentials, OktaAuth, RehlkoClient, RehlkoError
from custom_components.rehlko_energy.const import DOMAIN
from custom_components.rehlko_energy.diagnostics import async_get_config_entry_diagnostics
from custom_components.rehlko_energy.sidebar.snapshot import build_snapshot

from .conftest import FakeResponse, FakeSession, token_response
from .test_entities import SAMPLE_DETAILS, SAMPLE_DEVICE

EMAIL = "owner@example.com"
SECRETS = {
    "password": "pw-Zq7-never-shown",
    "client_secret": "cs-Zq7-never-shown",
    "api_key": "ak-Zq7-never-shown",
    "refresh_token": "rt-Zq7-never-shown",
}
ENTRY_DATA = {"username": EMAIL, "client_id": "client-id", "account_id": "acct-Zq7", **SECRETS}


def assert_no_secrets(text: str, *, also: tuple[str, ...] = ()) -> None:
    for name, secret in SECRETS.items():
        assert secret not in text, f"the {name} appears"
    for value in also:
        assert value not in text, f"{value!r} appears"


def make_auth(session: FakeSession, **kwargs) -> OktaAuth:
    return OktaAuth(
        session,
        AppCredentials("client-id", SECRETS["client_secret"], SECRETS["api_key"]),
        token_url="https://auth.example/oauth2/default/v1/token",
        scopes="openid offline_access",
        username=EMAIL,
        password=SECRETS["password"],
        refresh_token=SECRETS["refresh_token"],
        **kwargs,
    )


class Unreachable(FakeSession):
    def request(self, method, url, **kwargs):
        raise aiohttp.ClientConnectionError(f"Cannot connect to host for {url}")


@pytest.mark.parametrize(
    "response",
    [
        FakeResponse(400, {"error": "invalid_grant", "error_description": "Invalid credentials."}),
        FakeResponse(401, {"error": "invalid_client", "error_description": "Bad client."}),
        FakeResponse(403, {"error": "mfa_required", "mfa_token": "mfa-Zq7"}),
        FakeResponse(429, None),
        FakeResponse(500, None),
        FakeResponse(200, {"unexpected": True}),
        FakeResponse(200, None, _text="<html>proxy error</html>"),
    ],
    ids=["wrong-password", "wrong-client", "mfa", "rate-limit", "server-error", "no-token", "html"],
)
async def test_failed_sign_ins_never_log_or_raise_credentials(caplog, response) -> None:
    caplog.set_level(logging.DEBUG)
    auth = make_auth(FakeSession({("POST", "/token"): response}))
    with pytest.raises(RehlkoError) as raised:
        await auth.async_get_access_token()
    assert_no_secrets(f"{caplog.text} {raised.value} {raised.value!r} {auth!r} {auth.app!r}")


async def test_unreachable_services_never_log_or_raise_credentials(caplog) -> None:
    caplog.set_level(logging.DEBUG)
    auth = make_auth(Unreachable())
    with pytest.raises(RehlkoError) as raised:
        await auth.async_get_access_token()
    assert_no_secrets(f"{caplog.text} {raised.value!r}")

    # Signed in, then the API itself fails in each way it can.
    for api in (
        FakeResponse(401, {"message": "Unauthorized"}),
        FakeResponse(403, {"message": "Forbidden"}),
        FakeResponse(500, None),
        FakeResponse(302, None),
    ):
        session = FakeSession(
            {("POST", "/token"): FakeResponse(200, token_response()), ("GET", "/homes"): api}
        )
        client = RehlkoClient(session, make_auth(session), base_url="https://api.example")
        with pytest.raises(RehlkoError) as raised:
            await client.get_homes()
        issued = token_response()
        assert_no_secrets(
            f"{caplog.text} {raised.value} {raised.value!r}",
            also=(issued["access_token"], issued["refresh_token"]),
        )


@pytest.fixture
def client():
    api = MagicMock()
    for name, value in {
        "get_homes": [{"id": 1, "name": "Lake house", "devices": [SAMPLE_DEVICE]}],
        "get_device": SAMPLE_DETAILS,
        "get_events": [],
        "get_alerts": [],
        "get_notifications": [],
        "get_maintenance_notes": [{"id": 1, "contents": "Called Pat on 555-0100"}],
        "get_cell_plan": {},
        "get_me": {"id": "acct-Zq7", "email": EMAIL, "firstName": "Pat", "lastName": "Owner"},
        "get_notification_settings": {"sendShutdowns": True},
    }.items():
        setattr(api, name, AsyncMock(return_value=deepcopy(value)))
    api.base_url = "https://api.example"
    api.auth.claims = {"sub": "acct-Zq7", "email": EMAIL, "iss": "https://auth.example", "exp": 1}
    return api


async def test_diagnostics_snapshot_and_logs_hold_no_credentials(
    hass, client, caplog, enable_custom_integrations
) -> None:
    caplog.set_level(logging.DEBUG)
    entry = MockConfigEntry(domain=DOMAIN, title=EMAIL, unique_id="acct-Zq7", data=ENTRY_DATA)
    entry.add_to_hass(hass)
    with patch("custom_components.rehlko_energy.build_client", return_value=client):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        await entry.runtime_data.async_refresh()

    diagnostics = json.dumps(await async_get_config_entry_diagnostics(hass, entry), default=str)
    # Diagnostics are shared in bug reports: no credentials, and nothing that names the owner
    # or the site either.
    assert_no_secrets(
        diagnostics,
        also=(EMAIL, "acct-Zq7", "client-id", "SN123", "1 Example Way", "Pat", "555-0100"),
    )
    assert "batteryVoltageV" in diagnostics  # still useful

    # The panel is administrators-only, but it has no use for credentials at all.
    assert_no_secrets(json.dumps(build_snapshot(hass), default=str))
    # The log names the integration, not the account.
    assert_no_secrets(caplog.text, also=(EMAIL,))
