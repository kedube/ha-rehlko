"""Errors raised by the Rehlko API client."""

from __future__ import annotations

from typing import Any


class RehlkoError(Exception):
    """Base class for every error the client raises."""


class RehlkoConnectionError(RehlkoError):
    """The service could not be reached, timed out, or failed on its side (5xx)."""


class RehlkoAuthError(RehlkoError):
    """Okta rejected the credentials, or the refresh token is no longer valid.

    `reason` carries Okta's `error` code (for example `invalid_grant`) so the config flow
    can tell a wrong password from a misconfigured app credential.
    """

    def __init__(self, message: str, *, reason: str | None = None) -> None:
        super().__init__(message)
        self.reason = reason


class RehlkoAppCredentialsError(RehlkoAuthError):
    """Okta rejected the *app* credentials (client ID / secret), not the user's."""


class RehlkoApiError(RehlkoError):
    """The API answered with an error status.

    The service wraps errors in a V3 envelope:
    `{"errorVersion": "V3", "timestamp": ..., "statusCode": 400, "message": ..., "details": ...}`.
    """

    def __init__(
        self,
        status: int,
        message: str | None = None,
        *,
        details: Any = None,
        path: str | None = None,
    ) -> None:
        self.status = status
        self.message = message or f"HTTP {status}"
        self.details = details
        self.path = path
        super().__init__(f"{self.message} (HTTP {status}{f' {path}' if path else ''})")
