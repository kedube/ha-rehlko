"""scripts/capture.py: what --redact leaves out, and who can read a capture."""

from __future__ import annotations

import email.message
import importlib.util
import io
import json
import stat
import sys
import urllib.error
import urllib.request
import urllib.response
from pathlib import Path

import pytest

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


def test_a_capture_is_not_written_through_a_planted_symlink(tmp_path: Path) -> None:
    elsewhere = tmp_path / "someone_elses_file"
    elsewhere.write_text("theirs", encoding="utf-8")
    target = tmp_path / "rehlko_capture.json"
    target.symlink_to(elsewhere)
    with pytest.raises(OSError):
        capture.write_private(target, "{}")
    assert elsewhere.read_text(encoding="utf-8") == "theirs"


def test_a_redirect_is_refused_before_any_header_follows_it(monkeypatch) -> None:
    reached: list[str | None] = []

    class FakeNetwork(urllib.request.BaseHandler):
        handler_order = 100  # before the real HTTP handler

        def http_open(self, req):
            headers = email.message.Message()
            if req.host == "api.example.invalid":
                headers["Location"] = "http://elsewhere.example.invalid/stolen"
                response = urllib.response.addinfourl(io.BytesIO(b""), headers, req.full_url, 302)
                response.msg = "Found"
                return response
            reached.append(req.get_header("Authorization"))
            response = urllib.response.addinfourl(io.BytesIO(b"{}"), headers, req.full_url, 200)
            response.msg = "OK"
            return response

    base = "http://api.example.invalid"
    # Without the script's opener, urllib follows and takes the token along.
    request = urllib.request.Request(f"{base}/x", headers={"Authorization": "bearer token"})
    with urllib.request.build_opener(FakeNetwork).open(request):
        pass
    assert reached == ["bearer token"]
    reached.clear()

    assert any(isinstance(h, capture._NoRedirects) for h in capture.OPENER.handlers)
    monkeypatch.setattr(
        capture, "OPENER", urllib.request.build_opener(capture._NoRedirects, FakeNetwork)
    )
    with pytest.raises(urllib.error.HTTPError) as raised:
        capture.api_get(base, "token", "key", "/me")
    raised.value.close()
    assert raised.value.code == 302
    assert reached == []


def test_a_device_id_is_one_path_segment(monkeypatch) -> None:
    paths: list[str] = []
    monkeypatch.setattr(capture, "login", lambda *_args: "token")
    monkeypatch.setattr(capture, "working_base", lambda *_args: "https://api.example.invalid")

    def api_get(_base, _token, _key, path, **_params):
        paths.append(path)
        if path == "/homeowner/homes":
            return [{"id": 1, "devices": [{"id": "../../admin?x=1", "displayName": "Cabin"}]}]
        return {}

    monkeypatch.setattr(capture, "api_get", api_get)
    monkeypatch.setattr(capture, "write_private", lambda *_args: None)
    args = ["--client-id", "c", "--client-secret", "s", "--api-key", "k"]
    monkeypatch.setattr(sys, "argv", ["capture.py", *args, "--username", "u", "--password", "p"])
    capture.main()
    device_paths = [p for p in paths if p.startswith("/devices/")]
    assert device_paths and all(
        p.startswith("/devices/..%2F..%2Fadmin%3Fx%3D1") for p in device_paths
    )
