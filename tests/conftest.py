"""Shared fakes for the Rehlko tests.

Unit tests use these small transport fakes. Lifecycle, configuration-flow and sidebar
tests also use the Home Assistant test harness.
"""

from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture
def client():
    """The cloud client, answering with one home, one generator and empty feeds."""
    from .test_entities import SAMPLE_DETAILS, SAMPLE_DEVICE

    api = MagicMock()
    for name, value in {
        "get_homes": [{"id": 1, "devices": [SAMPLE_DEVICE]}],
        "get_device": SAMPLE_DETAILS,
        "get_events": [],
        "get_alerts": [],
        "get_notifications": [],
        "get_maintenance_notes": [],
        "get_cell_plan": {},
        "get_me": {"id": "owner"},
        "get_notification_settings": {"sendShutdowns": True, "sendWarnings": True},
    }.items():
        setattr(api, name, AsyncMock(return_value=deepcopy(value)))
    return api


@pytest.fixture(autouse=True)
def builtin_app(request):
    """Stands in for the app credentials written into the integration.

    Every test gets it, so none of them signs in with, compares or prints the real ones. The
    one test that checks the real set is there asks for it with `real_app_credentials`.
    """
    from custom_components.rehlko_energy import app_credentials
    from custom_components.rehlko_energy.api import AppCredentials

    if request.node.get_closest_marker("real_app_credentials"):
        yield app_credentials.BUILTIN
        return
    stand_in = AppCredentials("builtin-client", "builtin-secret", "builtin-key")
    with patch("custom_components.rehlko_energy.app_credentials.BUILTIN", stand_in):
        yield stand_in


@dataclass
class FakeResponse:
    status: int
    body: Any = None
    _text: str | None = None

    async def __aenter__(self) -> FakeResponse:
        return self

    async def __aexit__(self, *exc: object) -> None:
        return None

    async def text(self) -> str:
        if self._text is not None:
            return self._text
        return "" if self.body is None else json.dumps(self.body)

    async def json(self, content_type: str | None = None) -> Any:
        if self.body is None:
            raise ValueError("no json")
        return self.body


@dataclass
class Call:
    method: str
    url: str
    kwargs: dict[str, Any]


@dataclass
class FakeSession:
    """Serves queued responses and records the requests made.

    `handlers` maps (METHOD, path-substring) to a FakeResponse or a callable(Call)->FakeResponse.
    """

    handlers: dict[tuple[str, str], Any] = field(default_factory=dict)
    calls: list[Call] = field(default_factory=list)
    default: FakeResponse | None = None

    def _lookup(self, method: str, url: str) -> Any:
        for (m, frag), resp in self.handlers.items():
            if m == method and frag in url:
                return resp
        if self.default is not None:
            return self.default
        raise AssertionError(f"no handler for {method} {url}")

    def request(self, method: str, url: str, **kwargs: Any) -> FakeResponse:
        call = Call(method, url, kwargs)
        self.calls.append(call)
        resp = self._lookup(method, url)
        return resp(call) if callable(resp) else resp

    def post(self, url: str, **kwargs: Any) -> FakeResponse:
        return self.request("POST", url, **kwargs)

    def get(self, url: str, **kwargs: Any) -> FakeResponse:
        return self.request("GET", url, **kwargs)

    def last(self, method: str, frag: str) -> Call:
        for call in reversed(self.calls):
            if call.method == method and frag in call.url:
                return call
        raise AssertionError(f"no call for {method} {frag}")


def make_jwt(claims: dict[str, Any]) -> str:
    import base64

    def seg(obj: dict[str, Any]) -> str:
        return base64.urlsafe_b64encode(json.dumps(obj).encode()).decode().rstrip("=")

    return f"{seg({'alg': 'RS256'})}.{seg(claims)}.signature"


def token_response(**extra: Any) -> dict[str, Any]:
    body = {
        "access_token": make_jwt({"sub": "user-123", "iss": "okta"}),
        "id_token": make_jwt({"sub": "user-123", "email": "owner@example.com"}),
        "refresh_token": "refresh-abc",
        "expires_in": 3600,
        "scope": "openid profile offline_access email",
        "token_type": "Bearer",
    }
    body.update(extra)
    return body
