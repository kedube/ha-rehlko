"""scripts/capture.py: what --redact leaves out, and who can read a capture."""

from __future__ import annotations

import importlib.util
import json
import stat
from pathlib import Path

from custom_components.rehlko_energy.diagnostics import TO_REDACT

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location("capture", ROOT / "scripts" / "capture.py")
capture = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(capture)

# Shaped as the script writes it, with the personal fields the service sends.
CAPTURE = {
    "me": {"id": "acct-Zq7", "email": "owner@example.com", "firstName": "Pat", "lastName": "Kim"},
    "homes": [
        {
            "id": 1,
            "name": "Lake house",
            "address": {
                "address1": "1 Example Way",
                "city": "Smalltown",
                "postalCode": "00000",
                "lat": 12.34,
                "long": -56.78,
            },
            "devices": [
                {
                    "id": 1,
                    "serialNumber": "SN123",
                    "displayName": "Lake house",
                    "macAddress": "ff:ee:dd:cc:bb:aa",
                    "deviceIpAddress": "[::ffff:10.0.0.5]:42636",
                    "dealerOrgs": [{"name": "Example Power", "adminEmails": ["a@example.com"]}],
                }
            ],
        }
    ],
    "notification_settings": {"sendShutdowns": True},
    "generators": {
        "1": {
            "details": {"associatedUsers": ["kim@example.com"], "batteryVoltageV": 13.6},
            "notifications": [
                {"id": 7, "tag": "homeowneruser:acct-Zq7", "message": "Lake house has started"}
            ],
            "maintenance_notes": [{"id": 1, "contents": "Called on 555-0100"}],
        }
    },
}
PERSONAL = (
    "acct-Zq7",
    "example.com",
    "Pat",
    "Kim",
    "Lake house",
    "Example Way",
    "Smalltown",
    "00000",
    "12.34",
    "56.78",
    "SN123",
    "ff:ee:dd",
    "10.0.0.5",
    "Example Power",
    "555-0100",
)


def test_redact_leaves_out_what_diagnostics_leave_out() -> None:
    redacted = capture.redact_capture(CAPTURE)
    text = json.dumps(redacted)
    for value in PERSONAL:
        assert value not in text, value
    # What is not personal stays, and so does every field name.
    assert redacted["notification_settings"] == {"sendShutdowns": True}
    assert redacted["generators"]["1"]["details"]["batteryVoltageV"] == 13.6
    assert set(redacted["me"]) == set(CAPTURE["me"])
    assert CAPTURE["me"]["email"] == "owner@example.com"  # the original is left alone


def test_the_field_list_is_the_one_diagnostics_use() -> None:
    assert capture.load_privacy().PERSONAL_FIELDS == TO_REDACT


def test_a_capture_is_readable_by_its_owner_alone(tmp_path: Path) -> None:
    target = tmp_path / "rehlko_capture.json"
    target.write_text("old", encoding="utf-8")
    target.chmod(0o644)
    capture.write_private(target, "{}")
    assert stat.S_IMODE(target.stat().st_mode) == 0o600
    assert target.read_text(encoding="utf-8") == "{}"
