"""Payload fields that name a person, a place or a device, which diagnostics leave out.

This module must stay free of Home Assistant imports: `scripts/capture.py` loads it on its own,
so that a redacted capture leaves out the same fields as **Download diagnostics**.
"""

from __future__ import annotations

from typing import Any, Final

# The text Home Assistant's own `async_redact_data` puts in place of a value.
REDACTED: Final = "**REDACTED**"

PERSONAL_FIELDS: Final = frozenset(
    {
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
        # The same two addresses as the integration derives them (`GeneratorData.derived`).
        "ip_address",
        "mac_address",
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
)


def redact(data: Any, fields: frozenset[str] | set[str] = PERSONAL_FIELDS) -> Any:
    """`data` with the value of every key in `fields` replaced, at any depth.

    Empty values are left as they are, as Home Assistant's `async_redact_data` leaves them.
    """
    if isinstance(data, dict):
        return {
            key: REDACTED
            if key in fields and value is not None and value != ""
            else redact(value, fields)
            for key, value in data.items()
        }
    if isinstance(data, list):
        return [redact(value, fields) for value in data]
    return data
