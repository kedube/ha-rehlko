"""Async client for the Rehlko (Kohler) Energy Management `/kem/api/v3` REST API.

Every route below was recovered from the app's generated (swagger/Chopper) client, with its
HTTP method, path and body shape; docs/API.md documents them in full.

Requests carry two headers: `Authorization: bearer <Okta access token>` and `ApiKey: <app
API key>`. Device reads also take `sourceDeviceHost` (the device's `deviceHost`: `Hub`,
`REC` or `RET`), which routes the request to the right telemetry backend.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any
from urllib.parse import quote

import aiohttp

from .auth import OktaAuth
from .errors import RehlkoApiError, RehlkoAuthError, RehlkoConnectionError

_LOGGER = logging.getLogger(__name__)

API_PREFIX = "/kem/api/v3"
REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=45)


def _seg(value: Any) -> str:
    return quote(str(value), safe="")


def _items(data: Any, endpoint: str) -> list[dict[str, Any]]:
    if not isinstance(data, list) or any(not isinstance(item, dict) for item in data):
        raise RehlkoConnectionError(f"The {endpoint} endpoint returned an invalid response")
    return data


class RehlkoClient:
    """One signed-in account."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        auth: OktaAuth,
        *,
        base_url: str,
        user_agent: str = "HomeAssistant-RehlkoEnergy",
    ) -> None:
        self._session = session
        self._auth = auth
        self._base_url = base_url.rstrip("/")
        self._user_agent = user_agent
        self._requests = asyncio.Semaphore(6)

    @property
    def auth(self) -> OktaAuth:
        return self._auth

    @property
    def base_url(self) -> str:
        return self._base_url

    # ------------------------------------------------------------------ transport
    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        body: Any = None,
        _retry: bool = True,
    ) -> Any:
        token = await self._auth.async_get_access_token()
        headers = {
            "Authorization": f"bearer {token}",
            "ApiKey": self._auth.app.api_key,
            "Accept": "application/json",
            "User-Agent": self._user_agent,
        }
        query = {k: v for k, v in (params or {}).items() if v is not None}
        kwargs: dict[str, Any] = {
            "headers": headers,
            "params": query,
            "timeout": REQUEST_TIMEOUT,
            "allow_redirects": False,
        }
        if body is not None:
            kwargs["json"] = body
        url = f"{self._base_url}{API_PREFIX}{path}"
        try:
            async with self._requests, self._session.request(method, url, **kwargs) as resp:
                status = resp.status
                text = await resp.text()
        except (aiohttp.ClientError, TimeoutError) as err:
            raise RehlkoConnectionError(f"{method} {path}: {err}") from err

        if status == 401 and _retry:
            # The access token may have been revoked early; refresh once and retry.
            self._auth.invalidate()
            return await self._request(method, path, params=params, body=body, _retry=False)
        if status == 401:
            raise RehlkoAuthError("The API rejected the access token", reason="unauthorized")
        if status >= 500 or status == 429 or 300 <= status < 400:
            raise RehlkoConnectionError(f"{method} {path}: HTTP {status}")

        data: Any = None
        if text:
            try:
                data = json.loads(text)
            except json.JSONDecodeError:
                data = text
        if status >= 400:
            message = details = None
            if isinstance(data, dict):
                message = data.get("message") or data.get("title")
                details = data.get("details") or data.get("errors")
            elif isinstance(data, str):
                message = data[:200]
            raise RehlkoApiError(status, message, details=details, path=path)
        return data

    # ------------------------------------------------------------------ account
    async def get_me(self) -> dict[str, Any]:
        return await self._request("GET", "/homeowner/me") or {}

    async def get_homes(self) -> list[dict[str, Any]]:
        data = await self._request("GET", "/homeowner/homes")
        return _items(data, "homes")

    async def get_notification_settings(self) -> dict[str, Any]:
        return await self._request("GET", "/homeowner/settings/notification") or {}

    async def set_notification_settings(self, settings: dict[str, Any]) -> Any:
        """POST the full settings object (the app always sends every flag)."""
        return await self._request("POST", "/homeowner/settings/notification", body=settings)

    async def get_notifications(
        self, *, device_id: int | None = None, offset: int = 0, limit: int = 50
    ) -> list[dict[str, Any]]:
        data = await self._request(
            "GET",
            "/notifications",
            params={"DeviceId": device_id, "Offset": offset, "Limit": limit},
        )
        if isinstance(data, dict):  # tolerate a paged wrapper
            for key in ("items", "notifications", "results", "data"):
                if isinstance(data.get(key), list):
                    return _items(data[key], "notifications")
        return _items(data, "notifications")

    # ------------------------------------------------------------------ devices
    async def get_device(self, device_id: int, source_host: str | None = None) -> dict[str, Any]:
        data = await self._request(
            "GET", f"/devices/{_seg(device_id)}", params={"sourceDeviceHost": source_host}
        )
        if not isinstance(data, dict) or not data:
            raise RehlkoConnectionError("The device endpoint returned an invalid response")
        return data

    async def update_device(self, device_id: int, body: dict[str, Any]) -> Any:
        """PUT `{displayName, address, connectionType, installProgressType,
        autoFirmwareUpdateEnabled, completedInstallProgressSteps}`."""
        return await self._request("PUT", f"/devices/{_seg(device_id)}", body=body)

    async def get_events(
        self, device_id: int, source_host: str | None = None
    ) -> list[dict[str, Any]]:
        data = await self._request(
            "GET", f"/devices/{_seg(device_id)}/events", params={"sourceDeviceHost": source_host}
        )
        return _items(data, "events")

    async def get_alerts(
        self, device_id: int, source_host: str | None = None
    ) -> list[dict[str, Any]]:
        data = await self._request(
            "GET", f"/devices/{_seg(device_id)}/alerts", params={"sourceDeviceHost": source_host}
        )
        return _items(data, "alerts")

    async def get_maintenance_notes(self, device_id: int) -> list[dict[str, Any]]:
        data = await self._request("GET", f"/devices/{_seg(device_id)}/maintenance_notes")
        return _items(data, "maintenance notes")

    async def add_maintenance_note(self, device_id: int, contents: str) -> Any:
        return await self._request(
            "POST", f"/devices/{_seg(device_id)}/maintenance_notes", body={"contents": contents}
        )

    async def set_exercise_schedule(
        self,
        device_id: int,
        *,
        frequency: str,
        mode: str,
        duration_minutes: int,
        next_start: str | None,
    ) -> Any:
        body = {
            "frequency": frequency,
            "nextStartTimestamp": next_start,
            "mode": mode,
            "durationMinutes": int(duration_minutes),
        }
        return await self._request("PUT", f"/devices/{_seg(device_id)}/exercise", body=body)

    async def delete_exercise_schedule(self, device_id: int) -> Any:
        return await self._request("DELETE", f"/devices/{_seg(device_id)}/exercise")

    async def start_exercise(self, device_id: int, mode: str) -> Any:
        return await self._request(
            "POST", f"/devices/{_seg(device_id)}/exercise/start", body={"mode": mode}
        )

    async def stop_exercise(self, device_id: int) -> Any:
        return await self._request("POST", f"/devices/{_seg(device_id)}/exercise/stop")

    async def set_controller_clock(self, device_id: int, timestamp: str) -> Any:
        return await self._request(
            "POST",
            f"/devices/{_seg(device_id)}/set_controller_clock",
            body={"controllerClockTimestamp": timestamp},
        )

    async def set_peripheral_value(self, device_id: int, definition_id: Any, value: Any) -> Any:
        """Write one load-module / PIM parameter (`loadShed` / `pim` → `parameters[]`)."""
        return await self._request(
            "POST",
            f"/devices/{_seg(device_id)}/peripherals/{_seg(definition_id)}/set_value",
            body={"value": value},
        )

    async def rename_peripheral(self, device_id: int, definition_id: Any, display_name: str) -> Any:
        return await self._request(
            "PUT",
            f"/devices/{_seg(device_id)}/peripherals/{_seg(definition_id)}",
            body={"displayName": display_name},
        )

    async def get_cell_plan(self, device_id: int) -> dict[str, Any]:
        return await self._request("GET", f"/devices/cellplan/{_seg(device_id)}") or {}

    async def get_parameter_definitions(self, device_id: int, kind: str, serial_number: str) -> Any:
        """`kind` is `generators` or `ats`; `serial_number` comes from the details payload."""
        if kind not in ("generators", "ats"):
            raise ValueError(kind)
        return await self._request(
            "GET",
            f"/devices/{_seg(device_id)}/{kind}/{_seg(serial_number)}/parameters/definitions",
        )
