"""Small helpers shared by the client, the coordinator and the entities."""

from __future__ import annotations

import ipaddress
import math
import re
from datetime import UTC, datetime, tzinfo
from typing import Any

# Words that read better kept whole when splitting PascalCase wire values.
_ACRONYMS = {
    "ats": "ATS",
    "ecm": "ECM",
    "ecu": "ECU",
    "pim": "PIM",
    "rpm": "RPM",
    "gfci": "GFCI",
    "ism": "ISM",
    "nfpa": "NFPA",
    "j1939": "J1939",
    "kw": "kW",
    "lp": "LP",
    "lpg": "LPG",
    "ng": "NG",
    "ac": "AC",
    "dc": "DC",
    "usb": "USB",
    "mil": "MIL",
    "egr": "EGR",
    "iat": "IAT",
    "ect": "ECT",
    "tps": "TPS",
    "uego": "UEGO",
    "map": "MAP",
    "rsa": "RSA",
    "ok": "OK",
    "co": "CO",
    "afm": "AFM",
    "mj": "MJ",
    "bp": "BP",
    "chp": "CHP",
    "tip": "TIP",
    "cht": "CHT",
    "id": "ID",
    "ip": "IP",
    "rdc": "RDC",
    "rdc2": "RDC2",
    "vsg": "VSG",
    "apm": "APM",
    "rec": "REC",
    "ret": "RET",
    "can": "CAN",
    "pgen": "PGEN",
    "l1": "L1",
    "l2": "L2",
    "l3": "L3",
    "n": "N",
}
_SPLIT = re.compile(r"[A-Z]+(?=[A-Z][a-z])|[A-Z]?[a-z]+|[A-Z]+|\d+[A-Za-z]?")


def humanize(value: Any) -> str | None:
    """`LowOilPressureWarning` -> `Low oil pressure warning`; acronyms kept intact."""
    if value is None:
        return None
    text = str(value)
    if not text:
        return text
    if " " in text:
        return text[0].upper() + text[1:]
    parts = _SPLIT.findall(text) or [text]
    words = []
    for i, part in enumerate(parts):
        low = part.lower()
        if low in _ACRONYMS:
            words.append(_ACRONYMS[low])
        elif i == 0:
            words.append(part[0].upper() + part[1:].lower())
        else:
            words.append(low)
    return " ".join(words)


def slugify(value: Any) -> str:
    """`EveryOtherWeek` -> `every_other_week` (translation and option keys)."""
    text = re.sub(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])", "_", str(value))
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


def parse_timestamp(value: Any, default_tz: tzinfo | None = None) -> datetime | None:
    """Parse the API's ISO-8601 timestamps.

    The service mixes forms: `...Z`, `...+00:00`, seven-digit .NET fractions, and naive
    local wall-clock times. Naive values are given `default_tz` (the generator's site).
    """
    if not value or not isinstance(value, str):
        return None
    text = value.strip()
    if text.startswith("0001-01-01"):
        return None  # .NET DateTime.MinValue, i.e. "never"
    if text.endswith(("Z", "z")):
        text = text[:-1] + "+00:00"
    # Python accepts at most six fractional digits.
    text = re.sub(r"(\.\d{6})\d+", r"\1", text)
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=default_tz or UTC)
    return parsed


def has_offset(value: Any) -> bool | None:
    """Whether an API timestamp string carried a UTC offset (None if unknown)."""
    if not isinstance(value, str) or "T" not in value:
        return None
    return bool(re.search(r"(Z|z|[+-]\d{2}:?\d{2})$", value.strip()))


def format_timestamp(when: datetime, *, like: Any = None, site_tz: tzinfo | None = None) -> str:
    """Format `when` for a write, mirroring how the service formats the same field.

    If the value the service last returned carried an offset (or nothing is known), send
    an offset-qualified ISO string. If it was a naive wall-clock time, send the site's
    local wall-clock time without an offset, which is how the controller keeps time.
    """
    if when.tzinfo is None:
        when = when.replace(tzinfo=site_tz or UTC)
    if has_offset(like) is False:
        local = when.astimezone(site_tz) if site_tz else when
        return local.replace(tzinfo=None).isoformat(timespec="seconds")
    return when.isoformat(timespec="seconds")


def as_float(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
        return number if math.isfinite(number) else None
    except (TypeError, ValueError):
        return None


def first(*values: Any) -> Any:
    """The first value that is not None."""
    for value in values:
        if value is not None:
            return value
    return None


def plain_ip(value: Any) -> str | None:
    """The IP address in what the service reports, which is the socket it saw.

    `[::ffff:100.100.0.69]:42636` -> `100.100.0.69`: the port goes, and an IPv4 address
    written the IPv6 way is given as IPv4. Text that is not an address is returned as it is.
    """
    text = str(value).strip() if value is not None else ""
    if not text:
        return None
    if text.startswith("["):
        host = text[1:].partition("]")[0]
    elif text.count(":") == 1:
        host = text.partition(":")[0]  # IPv4 with a port; an IPv6 address has more colons
    else:
        host = text
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        return text
    mapped = getattr(address, "ipv4_mapped", None)
    return str(address if mapped is None else mapped)


_MAC_BYTE = re.compile(r"[0-9A-Fa-f]{2}")


def device_mac(value: Any) -> str | None:
    """The MAC address a device has on its network.

    The service sends the six bytes in reverse order: `91:E1:20:63:10:00` for a device whose
    address is `00:10:63:20:E1:91`. Home Assistant's own Rehlko integration turns them round
    in the same way. Anything that is not six bytes is returned as it is.
    """
    text = str(value).strip() if value is not None else ""
    if not text:
        return None
    parts = re.split(r"[:-]", text)
    if len(parts) != 6 or not all(_MAC_BYTE.fullmatch(part) for part in parts):
        return text
    return ":".join(reversed(parts))


def magnitude(value: Any) -> float | None:
    """A reading's size, for one whose sign carries no meaning (see `GeneratorData.load_watts`)."""
    number = as_float(value)
    return None if number is None else abs(number)
