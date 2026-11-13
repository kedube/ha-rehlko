"""REST client: headers, paths, verbs, 401 retry, error envelope, query params."""

from __future__ import annotations

import pytest

from custom_components.rehlko_energy.api.auth import AppCredentials, OktaAuth
from custom_components.rehlko_energy.api.client import RehlkoClient
from custom_components.rehlko_energy.api.errors import (
    RehlkoApiError,
    RehlkoAuthError,
    RehlkoConnectionError,
)

from .conftest import FakeResponse, FakeSession, token_response

APP = AppCredentials("client-id", "client-secret", "api-key-xyz")
BASE = "https://api.example"


def make_client(session: FakeSession) -> RehlkoClient:
    auth = OktaAuth(
        session, APP, token_url=f"{BASE}/token", scopes="s", username="u", password="pw"
    )
    return RehlkoClient(session, auth, base_url=BASE)


def with_token(handlers: dict) -> FakeSession:
    return FakeSession({("POST", "/token"): FakeResponse(200, token_response()), **handlers})


async def test_headers_include_bearer_and_apikey() -> None:
    session = with_token({("GET", "/homeowner/homes"): FakeResponse(200, [])})
    await make_client(session).get_homes()
    call = session.last("GET", "/homeowner/homes")
    headers = call.kwargs["headers"]
    assert headers["Authorization"].startswith("bearer ")
    assert headers["ApiKey"] == "api-key-xyz"


async def test_device_read_sends_source_host() -> None:
    session = with_token({("GET", "/devices/42"): FakeResponse(200, {"device": {"id": 42}})})
    await make_client(session).get_device(42, "Hub")
    call = session.last("GET", "/devices/42")
    assert call.kwargs["params"]["sourceDeviceHost"] == "Hub"
    assert call.url.endswith("/kem/api/v3/devices/42")


async def test_notifications_query_params() -> None:
    session = with_token({("GET", "/notifications"): FakeResponse(200, [])})
    await make_client(session).get_notifications(device_id=42, offset=10, limit=25)
    call = session.last("GET", "/notifications")
    assert call.kwargs["params"] == {"DeviceId": 42, "Offset": 10, "Limit": 25}


async def test_exercise_schedule_body_and_verb() -> None:
    session = with_token({("PUT", "/devices/42/exercise"): FakeResponse(200, {})})
    await make_client(session).set_exercise_schedule(
        42,
        frequency="Weekly",
        mode="Unloaded",
        duration_minutes=20,
        next_start="2026-11-22T14:00:00",
    )
    call = session.last("PUT", "/devices/42/exercise")
    assert call.kwargs["json"] == {
        "frequency": "Weekly",
        "nextStartTimestamp": "2026-11-22T14:00:00",
        "mode": "Unloaded",
        "durationMinutes": 20,
    }


async def test_start_and_stop_exercise() -> None:
    session = with_token(
        {
            ("POST", "/exercise/start"): FakeResponse(200, {}),
            ("POST", "/exercise/stop"): FakeResponse(200, {}),
        }
    )
    client = make_client(session)
    await client.start_exercise(7, "LoadedFullSpeed")
    assert session.last("POST", "/exercise/start").kwargs["json"] == {"mode": "LoadedFullSpeed"}
    await client.stop_exercise(7)
    assert "json" not in session.last("POST", "/exercise/stop").kwargs


async def test_set_peripheral_value_path_encoding() -> None:
    session = with_token({("POST", "/peripherals/"): FakeResponse(200, {})})
    await make_client(session).set_peripheral_value(7, "load 1", True)
    call = session.last("POST", "/peripherals/")
    assert "/peripherals/load%201/set_value" in call.url
    assert call.kwargs["json"] == {"value": True}


async def test_set_controller_clock() -> None:
    session = with_token({("POST", "/set_controller_clock"): FakeResponse(200, {})})
    await make_client(session).set_controller_clock(1, "2026-11-12T20:00:00")
    assert session.last("POST", "/set_controller_clock").kwargs["json"] == {
        "controllerClockTimestamp": "2026-11-12T20:00:00"
    }


async def test_401_refreshes_once_then_retries() -> None:
    attempts = {"n": 0}

    def homes(_call):
        attempts["n"] += 1
        return FakeResponse(401, {}) if attempts["n"] == 1 else FakeResponse(200, [{"id": 1}])

    session = FakeSession(
        {
            ("POST", "/token"): FakeResponse(200, token_response()),
            ("GET", "/homeowner/homes"): homes,
        }
    )
    result = await make_client(session).get_homes()
    assert result == [{"id": 1}]
    assert attempts["n"] == 2
    assert len([c for c in session.calls if "/token" in c.url]) == 2  # re-auth between tries


async def test_persistent_401_raises_auth_error() -> None:
    session = with_token({("GET", "/homeowner/homes"): FakeResponse(401, {})})
    with pytest.raises(RehlkoAuthError):
        await make_client(session).get_homes()


async def test_error_envelope_surfaced() -> None:
    session = with_token(
        {
            ("PUT", "/devices/42/exercise"): FakeResponse(
                400, {"statusCode": 400, "message": "Device offline", "details": {"x": 1}}
            )
        }
    )
    with pytest.raises(RehlkoApiError) as err:
        await make_client(session).set_exercise_schedule(
            42, frequency="Weekly", mode="Unloaded", duration_minutes=20, next_start=None
        )
    assert err.value.status == 400
    assert err.value.message == "Device offline"
    assert err.value.details == {"x": 1}


async def test_5xx_is_connection_error() -> None:
    session = with_token({("GET", "/homeowner/homes"): FakeResponse(502, {})})
    with pytest.raises(RehlkoConnectionError):
        await make_client(session).get_homes()


async def test_notifications_unwraps_paged_dict() -> None:
    session = with_token(
        {("GET", "/notifications"): FakeResponse(200, {"items": [{"id": 1}], "total": 1})}
    )
    assert await make_client(session).get_notifications() == [{"id": 1}]


async def test_parameter_definitions_rejects_bad_kind() -> None:
    session = with_token({})
    with pytest.raises(ValueError):
        await make_client(session).get_parameter_definitions(1, "bogus", "SN")


@pytest.mark.parametrize("status", [302, 307, 429])
async def test_redirects_and_rate_limits_are_transient(status) -> None:
    session = with_token({("GET", "/homeowner/homes"): FakeResponse(status, {})})
    with pytest.raises(RehlkoConnectionError):
        await make_client(session).get_homes()
    assert session.last("GET", "/homeowner/homes").kwargs["allow_redirects"] is False


@pytest.mark.parametrize("body", [None, {}, {"items": []}, ["bad-item"], "<html>error</html>"])
async def test_malformed_homes_are_not_a_successful_empty_account(body) -> None:
    session = with_token({("GET", "/homeowner/homes"): FakeResponse(200, body)})
    with pytest.raises(RehlkoConnectionError):
        await make_client(session).get_homes()


async def test_malformed_alerts_do_not_clear_existing_alerts() -> None:
    session = with_token({("GET", "/alerts"): FakeResponse(200, {"error": "unavailable"})})
    with pytest.raises(RehlkoConnectionError):
        await make_client(session).get_alerts(1)
