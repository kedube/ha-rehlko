"""Okta authentication for the Rehlko (Kohler) Energy Management API.

The mobile app signs in through AppAuth (authorization code + PKCE in a browser tab), but
its Okta client is also permitted the OAuth 2.0 resource-owner password grant, which is
what a headless Home Assistant install needs. Tokens are standard Okta tokens from the
`default` authorization server: a JWT access token (about an hour), an ID token, and —
because the `offline_access` scope is requested — a refresh token.

The client authenticates to the token endpoint with HTTP Basic (`client_secret_basic`).
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import math
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

import aiohttp

from .errors import (
    RehlkoAppCredentialsError,
    RehlkoAuthError,
    RehlkoConnectionError,
)

_LOGGER = logging.getLogger(__name__)

# Refresh this long before the access token's stated expiry.
EXPIRY_SKEW = 120.0
REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=30)


@dataclass(slots=True)
class TokenSet:
    """The tokens from one successful token-endpoint call.

    The tokens and the claims (which name the account) are left out of the repr, so a log
    line, an assertion message or a traceback that formats this object cannot leak them.
    """

    access_token: str = field(repr=False)
    expires_at: float
    refresh_token: str | None = field(default=None, repr=False)
    id_token: str | None = field(default=None, repr=False)
    scope: str | None = None
    claims: dict[str, Any] = field(default_factory=dict, repr=False)

    @property
    def expired(self) -> bool:
        return time.time() >= self.expires_at - EXPIRY_SKEW


@dataclass(frozen=True, slots=True)
class AppCredentials:
    """The app's OAuth client and API-gateway identifiers (see `app_credentials.py`)."""

    client_id: str
    client_secret: str = field(repr=False)
    api_key: str = field(repr=False)


def decode_jwt_claims(token: str | None) -> dict[str, Any]:
    """Return a JWT's payload without verifying it (used only for display and IDs)."""
    if not isinstance(token, str) or token.count(".") != 2:
        return {}
    payload = token.split(".")[1]
    payload += "=" * (-len(payload) % 4)
    try:
        claims = json.loads(base64.urlsafe_b64decode(payload))
        return claims if isinstance(claims, dict) else {}
    except (ValueError, json.JSONDecodeError):
        return {}


class OktaAuth:
    """Holds the token set and keeps the access token fresh.

    `on_refresh_token` is called whenever Okta issues a new refresh token, so the caller can
    persist it (Okta may rotate refresh tokens on every use).
    """

    def __init__(
        self,
        session: aiohttp.ClientSession,
        app: AppCredentials,
        *,
        token_url: str,
        scopes: str,
        username: str,
        password: str | None = None,
        refresh_token: str | None = None,
        on_refresh_token: Callable[[str], Awaitable[None] | None] | None = None,
    ) -> None:
        self._session = session
        self._app = app
        self._token_url = token_url
        self._scopes = scopes
        self._username = username
        self._password = password
        self._refresh_token = refresh_token
        self._on_refresh_token = on_refresh_token
        self._tokens: TokenSet | None = None
        self._lock = asyncio.Lock()

    @property
    def app(self) -> AppCredentials:
        return self._app

    @property
    def tokens(self) -> TokenSet | None:
        return self._tokens

    @property
    def refresh_token(self) -> str | None:
        return self._refresh_token

    @property
    def claims(self) -> dict[str, Any]:
        return self._tokens.claims if self._tokens else {}

    def invalidate(self) -> None:
        """Forget the access token so the next request refreshes it (e.g. after a 401)."""
        if self._tokens is not None:
            self._tokens.expires_at = 0

    async def async_get_access_token(self) -> str:
        async with self._lock:
            if self._tokens is None or self._tokens.expired:
                await self._async_obtain()
            assert self._tokens is not None
            return self._tokens.access_token

    async def async_login(self) -> TokenSet:
        """Sign in with the password grant, ignoring any stored refresh token."""
        async with self._lock:
            if not self._password:
                raise RehlkoAuthError("No password available", reason="no_password")
            await self._async_password_grant()
            assert self._tokens is not None
            return self._tokens

    async def _async_obtain(self) -> None:
        if self._refresh_token:
            try:
                await self._async_refresh_grant()
                return
            except RehlkoAppCredentialsError:
                raise
            except RehlkoAuthError as err:
                if not self._password:
                    raise
                _LOGGER.debug("Refresh token rejected (%s); signing in again", err.reason)
        if not self._password:
            raise RehlkoAuthError("Sign-in required", reason="no_credentials")
        await self._async_password_grant()

    async def _async_password_grant(self) -> None:
        await self._async_token_request(
            {
                "grant_type": "password",
                "username": self._username,
                "password": self._password or "",
                "scope": self._scopes,
            }
        )

    async def _async_refresh_grant(self) -> None:
        await self._async_token_request(
            {
                "grant_type": "refresh_token",
                "refresh_token": self._refresh_token or "",
                "scope": self._scopes,
            }
        )

    async def _async_token_request(self, form: dict[str, str]) -> None:
        # HTTP Basic, written out: aiohttp is retiring its `BasicAuth` helper.
        credentials = f"{self._app.client_id}:{self._app.client_secret}".encode()
        basic = base64.b64encode(credentials).decode("ascii")
        try:
            async with self._session.post(
                self._token_url,
                data=form,
                headers={"Accept": "application/json", "Authorization": f"Basic {basic}"},
                timeout=REQUEST_TIMEOUT,
                allow_redirects=False,
            ) as resp:
                try:
                    body: dict[str, Any] = await resp.json(content_type=None)
                except (aiohttp.ContentTypeError, json.JSONDecodeError, ValueError):
                    body = {}
                status = resp.status
        except (aiohttp.ClientError, TimeoutError) as err:
            raise RehlkoConnectionError(f"Okta unreachable: {err}") from err

        if status >= 500 or status == 429 or 300 <= status < 400:
            raise RehlkoConnectionError(f"Okta returned HTTP {status}")
        if not isinstance(body, dict):
            raise RehlkoConnectionError("Okta returned an invalid token response")
        if status == 200 and "access_token" not in body:
            raise RehlkoConnectionError("Okta returned an invalid token response")
        if status != 200 or "access_token" not in body:
            error = str(body.get("error") or f"http_{status}")
            description = str(body.get("error_description") or "Authentication failed")
            if error in ("invalid_client", "unauthorized_client"):
                raise RehlkoAppCredentialsError(description, reason=error)
            raise RehlkoAuthError(description, reason=error)

        try:
            expires_in = float(body.get("expires_in", 3600))
        except (TypeError, ValueError) as err:
            raise RehlkoConnectionError("Okta returned an invalid token expiry") from err
        if (
            not isinstance(body["access_token"], str)
            or not body["access_token"]
            or not math.isfinite(expires_in)
            or expires_in <= 0
        ):
            raise RehlkoConnectionError("Okta returned an invalid token response")
        id_token = body.get("id_token")
        claims = decode_jwt_claims(id_token) or decode_jwt_claims(body["access_token"])
        self._tokens = TokenSet(
            access_token=body["access_token"],
            expires_at=time.time() + expires_in,
            refresh_token=body.get("refresh_token") or self._refresh_token,
            id_token=id_token or (self._tokens.id_token if self._tokens else None),
            scope=body.get("scope"),
            claims=claims or (self._tokens.claims if self._tokens else {}),
        )
        new_refresh = body.get("refresh_token")
        if new_refresh and new_refresh != self._refresh_token:
            self._refresh_token = new_refresh
            if self._on_refresh_token is not None:
                result = self._on_refresh_token(new_refresh)
                if asyncio.iscoroutine(result):
                    await result
