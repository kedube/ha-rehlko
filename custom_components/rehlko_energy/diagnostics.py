"""Diagnostics: every payload the integration holds, with personal data redacted."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant

from . import RehlkoConfigEntry
from .app_credentials import stored_app_credentials
from .const import (
    CONF_ACCOUNT_ID,
    CONF_API_KEY,
    CONF_CLIENT_ID,
    CONF_CLIENT_SECRET,
    CONF_REFRESH_TOKEN,
)

TO_REDACT_ENTRY = {
    CONF_USERNAME,
    CONF_PASSWORD,
    CONF_REFRESH_TOKEN,
    CONF_CLIENT_SECRET,
    CONF_API_KEY,
    CONF_CLIENT_ID,
    CONF_ACCOUNT_ID,
}
TO_REDACT = {
    # identity and contact
    "email",
    "firstName",
    "lastName",
    "adminEmails",
    "inviterFirstName",
    "inviterLastName",
    "e164PhoneNumber",
    "displayPhoneNumber",
    "userId",
    # A notification's `tag` is `homeowneruser:` and the account's user number.
    "tag",
    "dealerAuthor",
    "addedBy",
    "associatedUsers",
    "users",
    "deviceSerialNumbers",
    "inviteCode",
    "pendingInviteCode",
    "businessPartnerNo",
    "name",
    "displayName",
    # Free text and links can embed addresses, customer names or account identifiers.
    "contents",
    "message",
    "ctaLink",
    # location
    "address",
    "address1",
    "address2",
    "city",
    "postalCode",
    "lat",
    "long",
    "latitude",
    "longitude",
    # device identity and network
    "serialNumber",
    "macAddress",
    "deviceIpAddress",
    "serverIpAddress",
    # Not seen in the payloads so far, but identifying if a hub or cell kit ever reports them.
    "ssid",
    "wifiSsid",
    "imei",
    "iccid",
    "imsi",
    "msisdn",
    "phoneNumber",
    # tokens
    "token",
    "accessToken",
    "refreshToken",
    "idToken",
}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: RehlkoConfigEntry
) -> dict[str, Any]:
    coordinator = entry.runtime_data
    data = coordinator.data
    generators = {}
    if data is not None:
        for device_id, gen in data.generators.items():
            generators[str(device_id)] = {
                "home": {k: v for k, v in gen.home.items() if k != "devices"},
                "device": gen.device,
                "details": gen.details,
                "alerts": gen.alerts,
                "events": gen.events[:100],
                "maintenance_notes": gen.maintenance_notes,
                "notifications": gen.notifications[:50],
                "cell_plan": gen.cell_plan,
                "derived": {
                    "is_connected": gen.is_connected,
                    "is_running": gen.is_running,
                    "is_exercising": gen.is_exercising,
                    "on_generator_power": gen.on_generator_power,
                    "utility_present": gen.utility_present,
                    "ready_to_run": gen.ready_to_run,
                    "has_schedule": gen.has_schedule,
                    "e_stop_engaged": gen.e_stop_engaged,
                },
                "details_updated": gen.details_updated.isoformat() if gen.details_updated else None,
                "feeds_updated": gen.feeds_updated.isoformat() if gen.feeds_updated else None,
            }
    return {
        "entry": {
            "data": async_redact_data(dict(entry.data), TO_REDACT_ENTRY),
            "options": dict(entry.options),
        },
        "api": {
            "base_url": coordinator.client.base_url,
            # Whether the entry signs in with app credentials entered by hand ("stored") or
            # with the ones written into the integration ("built_in").
            "app_credentials": "stored" if stored_app_credentials(entry.data) else "built_in",
            # `aud` (in an ID token) and `cid` (in an access token) are the app's client ID,
            # which is redacted in the entry's data above.
            "token_claims": async_redact_data(
                {
                    k: v
                    for k, v in coordinator.client.auth.claims.items()
                    if k in ("iss", "aud", "scp", "exp", "iat", "cid", "ver")
                },
                {"aud", "cid"},
            ),
        },
        "coordinator": {
            "last_update_success": coordinator.last_update_success,
            "update_interval_seconds": coordinator.update_interval.total_seconds()
            if coordinator.update_interval
            else None,
        },
        "account": {
            # The profile's `id` is the account's identity; a generator's `id` is kept below
            # because the service's routes are built from it.
            "me": async_redact_data(data.me if data else {}, TO_REDACT | {"id"}),
            "notification_settings": data.notification_settings if data else None,
        },
        "generators": async_redact_data(generators, TO_REDACT),
    }
