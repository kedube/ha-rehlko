"""Okta auth: password grant, refresh, rotation, error mapping, token caching."""

from __future__ import annotations

import base64
import time

import pytest

from custom_components.rehlko_energy.api.auth import AppCredentials, OktaAuth, decode_jwt_claims
from custom_components.rehlko_energy.api.errors import (
    RehlkoAppCredentialsError,
    RehlkoAuthError,
    RehlkoConnectionError,
)

from .conftest import FakeResponse, FakeSession, make_jwt, token_response

APP = AppCredentials("client-id", "client-secret", "api-key")
TOKEN_URL = "https://auth.example/oauth2/default/v1/token"
SCOPES = "openid profile offline_access email"


def make_auth(session: FakeSession, **kwargs) -> OktaAuth:
    return OktaAuth(
        session, APP, token_url=TOKEN_URL, scopes=SCOPES, username="owner@example.com", **kwargs
    )


async def test_password_grant_sends_basic_auth_and_form() -> None:
    session = FakeSession({("POST", "/token"): FakeResponse(200, token_response())})
    auth = make_auth(session, password="pw")
    token = await auth.async_get_access_token()
    assert token
    call = session.last("POST", "/token")
    # The app's credentials go in an HTTP Basic header, as Okta's `client_secret_basic` expects.
    scheme, _, encoded = call.kwargs["headers"]["Authorization"].partition(" ")
    assert scheme == "Basic"
    assert base64.b64decode(encoded).decode() == "client-id:client-secret"
    assert call.kwargs["data"]["grant_type"] == "password"
    assert call.kwargs["data"]["username"] == "owner@example.com"
    assert auth.refresh_token == "refresh-abc"
    assert auth.claims["email"] == "owner@example.com"


async def test_access_token_is_cached_until_near_expiry() -> None:
    session = FakeSession({("POST", "/token"): FakeResponse(200, token_response())})
    auth = make_auth(session, password="pw")
    await auth.async_get_access_token()
    await auth.async_get_access_token()
    assert len([c for c in session.calls if "/token" in c.url]) == 1


async def test_invalidate_forces_refresh() -> None:
    session = FakeSession({("POST", "/token"): FakeResponse(200, token_response())})
    auth = make_auth(session, password="pw")
    await auth.async_get_access_token()
    auth.invalidate()
    await auth.async_get_access_token()
    assert len([c for c in session.calls if "/token" in c.url]) == 2


async def test_refresh_grant_used_when_token_present() -> None:
    session = FakeSession(
        {("POST", "/token"): FakeResponse(200, token_response(refresh_token="refresh-xyz"))}
    )
    auth = make_auth(session, refresh_token="refresh-abc")
    await auth.async_get_access_token()
    call = session.last("POST", "/token")
    assert call.kwargs["data"]["grant_type"] == "refresh_token"
    assert call.kwargs["data"]["refresh_token"] == "refresh-abc"


async def test_rotated_refresh_token_triggers_callback() -> None:
    saved: list[str] = []
    session = FakeSession(
        {("POST", "/token"): FakeResponse(200, token_response(refresh_token="refresh-new"))}
    )
    auth = make_auth(
        session, refresh_token="refresh-old", on_refresh_token=lambda t: saved.append(t)
    )
    await auth.async_get_access_token()
    assert saved == ["refresh-new"]
    assert auth.refresh_token == "refresh-new"


async def test_refresh_failure_falls_back_to_password() -> None:
    responses = iter(
        [
            FakeResponse(400, {"error": "invalid_grant", "error_description": "expired"}),
            FakeResponse(200, token_response()),
        ]
    )
    session = FakeSession({("POST", "/token"): lambda _call: next(responses)})
    auth = make_auth(session, password="pw", refresh_token="stale")
    token = await auth.async_get_access_token()
    assert token
    assert len([c for c in session.calls if "/token" in c.url]) == 2


async def test_bad_app_credentials_do_not_fall_back() -> None:
    session = FakeSession(
        {
            ("POST", "/token"): FakeResponse(
                401, {"error": "invalid_client", "error_description": "bad client"}
            )
        }
    )
    auth = make_auth(session, password="pw", refresh_token="stale")
    with pytest.raises(RehlkoAppCredentialsError):
        await auth.async_get_access_token()
    # Only the refresh attempt; no password fallback for a client-credential problem.
    assert len([c for c in session.calls if "/token" in c.url]) == 1


async def test_wrong_password_raises_auth_error() -> None:
    session = FakeSession(
        {
            ("POST", "/token"): FakeResponse(
                400, {"error": "invalid_grant", "error_description": "bad"}
            )
        }
    )
    auth = make_auth(session, password="wrong")
    with pytest.raises(RehlkoAuthError) as err:
        await auth.async_login()
    assert err.value.reason == "invalid_grant"


async def test_server_error_is_connection_error() -> None:
    session = FakeSession({("POST", "/token"): FakeResponse(503, {})})
    auth = make_auth(session, password="pw")
    with pytest.raises(RehlkoConnectionError):
        await auth.async_get_access_token()


async def test_expired_property() -> None:
    session = FakeSession({("POST", "/token"): FakeResponse(200, token_response(expires_in=1))})
    auth = make_auth(session, password="pw")
    await auth.async_get_access_token()
    tokens = auth.tokens
    assert tokens is not None
    tokens.expires_at = time.time() - 1
    assert tokens.expired


def test_decode_jwt_claims_handles_garbage() -> None:
    assert decode_jwt_claims(None) == {}
    assert decode_jwt_claims("not-a-jwt") == {}
    assert decode_jwt_claims(make_jwt({"sub": "x"})) == {"sub": "x"}


@pytest.mark.parametrize("status", [302, 429, 503])
async def test_transient_token_errors_do_not_trigger_reauthentication(status) -> None:
    session = FakeSession({("POST", "/token"): FakeResponse(status, {})})
    auth = make_auth(session, password="pw")
    with pytest.raises(RehlkoConnectionError):
        await auth.async_get_access_token()
    assert session.last("POST", "/token").kwargs["allow_redirects"] is False


@pytest.mark.parametrize(
    "body", [[], "unexpected", {"access_token": None}, token_response(expires_in="NaN")]
)
async def test_malformed_token_responses_are_connection_errors(body) -> None:
    session = FakeSession({("POST", "/token"): FakeResponse(200, body)})
    with pytest.raises(RehlkoConnectionError):
        await make_auth(session, password="pw").async_get_access_token()


def test_secrets_are_not_part_of_any_repr() -> None:
    """A log line or traceback that formats these objects must not leak what they hold."""
    from custom_components.rehlko_energy.api import AppCredentials, TokenSet

    app = AppCredentials("client-id", "s3cret-value", "api-key-value")
    tokens = TokenSet(
        access_token="access-value",
        expires_at=1.0,
        refresh_token="refresh-value",
        id_token="id-value",
        claims={"email": "owner@example.com"},
    )
    shown = f"{app!r} {app} {tokens!r} {tokens}"
    assert "client-id" in shown
    for secret in (
        "s3cret-value",
        "api-key-value",
        "access-value",
        "refresh-value",
        "id-value",
        "owner@example.com",
    ):
        assert secret not in shown
