"""Config-flow helpers: error mapping and the sign-in/host-fallback validator."""

from __future__ import annotations

import pytest

from custom_components.rehlko_energy.api import (
    AppCredentials,
    RehlkoApiError,
    RehlkoAppCredentialsError,
    RehlkoAuthError,
    RehlkoConnectionError,
)
from custom_components.rehlko_energy.config_flow import (
    _app_credentials,
    _error_key,
    async_validate,
)

from .conftest import FakeResponse, FakeSession, token_response

APP = AppCredentials("cid", "secret", "key")


def test_error_key_mapping() -> None:
    assert (
        _error_key(RehlkoAppCredentialsError("x", reason="invalid_client"))
        == "invalid_app_credentials"
    )
    assert _error_key(RehlkoAuthError("x", reason="unauthorized")) == "invalid_api_key"
    assert _error_key(RehlkoAuthError("x", reason="invalid_grant")) == "invalid_auth"
    assert _error_key(RehlkoApiError(403)) == "invalid_api_key"
    assert _error_key(RehlkoConnectionError("x")) == "cannot_connect"
    assert _error_key(ValueError("x")) == "unknown"


def test_app_credentials_lose_the_env_files_quotes_and_padding() -> None:
    """The app's .env reads NAME='value'; pasting the quotes must not break sign-in."""
    pasted = {"client_id": " 'cid' ", "client_secret": '"sec\'ret"', "api_key": "key\n"}
    assert _app_credentials(pasted) == AppCredentials("cid", "sec'ret", "key")
    # A lone or unmatched quote is part of the value.
    odd = {"client_id": "'", "client_secret": "'abc", "api_key": 'abc"'}
    assert _app_credentials(odd) == AppCredentials("'", "'abc", 'abc"')


class FakeHass:
    """Only what async_validate uses: a shared aiohttp session via async_get_clientsession."""

    def __init__(self, session: FakeSession) -> None:
        self._session = session


@pytest.fixture(autouse=True)
def _patch_session(monkeypatch):
    import custom_components.rehlko_energy.config_flow as cf

    monkeypatch.setattr(cf, "async_get_clientsession", lambda hass: hass._session)


async def test_validate_signs_in_counts_generators_and_picks_host() -> None:
    homes = [{"devices": [{"id": 1}, {"id": 2}]}]
    session = FakeSession(
        {
            ("POST", "/token"): FakeResponse(200, token_response()),
            ("GET", "/homeowner/homes"): FakeResponse(200, homes),
            ("GET", "/homeowner/me"): FakeResponse(200, {"id": "acct-9"}),
        }
    )
    result = await async_validate(FakeHass(session), "owner@example.com", "pw", APP)
    assert result.generators == 2
    assert result.account_id == "acct-9"
    assert result.refresh_token == "refresh-abc"
    assert result.base_url.startswith("https://")


async def test_validate_falls_back_to_second_host() -> None:
    homes = [{"devices": [{"id": 1}]}]
    first_base = "api.hems.rehlko.com"

    def homes_handler(call):
        # The first host errors at the connection level; the second answers.
        if first_base in call.url:
            return FakeResponse(503, {})
        return FakeResponse(200, homes)

    session = FakeSession(
        {
            ("POST", "/token"): FakeResponse(200, token_response()),
            ("GET", "/homeowner/homes"): homes_handler,
            ("GET", "/homeowner/me"): FakeResponse(200, {"id": "acct-1"}),
        }
    )
    result = await async_validate(FakeHass(session), "owner@example.com", "pw", APP)
    assert "rk-prod" in result.base_url
    assert result.generators == 1


async def test_validate_propagates_auth_error() -> None:
    session = FakeSession(
        {
            ("POST", "/token"): FakeResponse(
                400, {"error": "invalid_grant", "error_description": "bad"}
            )
        }
    )
    with pytest.raises(RehlkoAuthError):
        await async_validate(FakeHass(session), "owner@example.com", "wrong", APP)
