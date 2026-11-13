#!/usr/bin/env python3
"""Sign in to Rehlko Energy Management and dump an account's payloads to JSON.

A standalone tool (Python standard library only) for inspecting the live API against your own
account — handy for verifying the integration or refreshing docs/API.md. Output contains your
serial number, address and tokens: keep it private and never commit it.

Credentials can come from the installed app's .env (--from-app), from flags, or from the
environment (REHLKO_USERNAME/PASSWORD/CLIENT_ID/CLIENT_SECRET/API_KEY).

Examples:
  python3 scripts/capture.py --from-app --username you@example.com --password - --out captures
  REHLKO_USERNAME=... REHLKO_PASSWORD=... python3 scripts/capture.py --from-app
"""

from __future__ import annotations

import argparse
import base64
import getpass
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ISSUER = "https://auth.home.kohlergenerators.com/oauth2/default"
TOKEN_URL = f"{ISSUER}/v1/token"
SCOPES = "openid profile offline_access email"
BASE_URLS = ["https://api.hems.rehlko.com", "https://api.rk-prod.energymanagement.dev"]
PREFIX = "/kem/api/v3"
DEFAULT_APP = os.environ.get("REHLKO_APP", "/Applications/Energy Mgmt..app")
ENV_REL = "Wrapper/Runner.app/Frameworks/App.framework/flutter_assets/.env"


def read_app_env(app_path: str) -> dict[str, str]:
    env_file = Path(app_path) / ENV_REL
    values: dict[str, str] = {}
    for line in env_file.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^([A-Z_]+)='(.*)'\s*$", line.strip())
        if m:
            values[m.group(1)] = m.group(2)
    return values


def _post_form(url: str, form: dict[str, str], headers: dict[str, str]) -> dict:
    data = urllib.parse.urlencode(form).encode()
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as err:
        raise SystemExit(f"Token request failed ({err.code}): {err.read().decode()[:300]}") from err


def login(client_id: str, client_secret: str, username: str, password: str) -> str:
    basic = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    body = _post_form(
        TOKEN_URL,
        {"grant_type": "password", "username": username, "password": password, "scope": SCOPES},
        {
            "Authorization": f"Basic {basic}",
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
        },
    )
    token = body.get("access_token")
    if not token:
        raise SystemExit(f"No access token: {body}")
    return token


def api_get(base_url: str, token: str, api_key: str, path: str, **params: object) -> object:
    query = {k: v for k, v in params.items() if v is not None}
    url = f"{base_url}{PREFIX}{path}"
    if query:
        url += "?" + urllib.parse.urlencode(query)
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"bearer {token}",
            "ApiKey": api_key,
            "Accept": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=45) as resp:
        return json.loads(resp.read())


def working_base(token: str, api_key: str) -> str:
    for base in BASE_URLS:
        try:
            api_get(base, token, api_key, "/homeowner/homes")
            return base
        except urllib.error.HTTPError as err:
            if err.code in (401, 403):
                raise SystemExit(
                    f"API rejected the request ({err.code}); check the API key."
                ) from err
        except (urllib.error.URLError, TimeoutError):
            continue
    raise SystemExit("No API host answered.")


def main() -> int:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument(
        "--from-app",
        nargs="?",
        const=DEFAULT_APP,
        help="Read client id/secret/API key from the installed app's .env.",
    )
    p.add_argument("--client-id", default=os.environ.get("REHLKO_CLIENT_ID"))
    p.add_argument("--client-secret", default=os.environ.get("REHLKO_CLIENT_SECRET"))
    p.add_argument("--api-key", default=os.environ.get("REHLKO_API_KEY"))
    p.add_argument("--username", default=os.environ.get("REHLKO_USERNAME"))
    p.add_argument(
        "--password", default=os.environ.get("REHLKO_PASSWORD"), help="Password, or - to prompt."
    )
    p.add_argument(
        "--out", type=Path, help="Directory to write JSON into (default: print a summary only)."
    )
    p.add_argument(
        "--redact", action="store_true", help="Blank serial numbers and addresses in the output."
    )
    args = p.parse_args()

    app = read_app_env(args.from_app) if args.from_app else {}
    client_id = args.client_id or app.get("CLIENT_ID")
    client_secret = args.client_secret or app.get("CLIENT_SECRET")
    api_key = args.api_key or app.get("API_KEY")
    username = args.username or input("Email: ").strip()
    password = args.password
    if not password or password == "-":
        password = getpass.getpass("Password: ")
    if not all([client_id, client_secret, api_key]):
        raise SystemExit("Missing client id/secret/API key (use --from-app or flags).")

    token = login(client_id, client_secret, username, password)
    base = working_base(token, api_key)
    print(f"Signed in. API host: {base}", file=sys.stderr)

    homes = api_get(base, token, api_key, "/homeowner/homes")
    me = api_get(base, token, api_key, "/homeowner/me")
    settings = api_get(base, token, api_key, "/homeowner/settings/notification")
    out: dict[str, object] = {
        "me": me,
        "homes": homes,
        "notification_settings": settings,
        "generators": {},
    }

    for home in homes if isinstance(homes, list) else []:
        for device in home.get("devices") or []:
            did, host = device.get("id"), device.get("deviceHost")
            print(f"  generator {did} ({device.get('displayName')})", file=sys.stderr)
            bundle = {"summary": device}
            for key, path in (
                ("details", f"/devices/{did}"),
                ("events", f"/devices/{did}/events"),
                ("alerts", f"/devices/{did}/alerts"),
                ("maintenance_notes", f"/devices/{did}/maintenance_notes"),
                ("notifications", "/notifications"),
            ):
                try:
                    bundle[key] = api_get(
                        base,
                        token,
                        api_key,
                        path,
                        sourceDeviceHost=host if "devices" in path else None,
                        DeviceId=did if path == "/notifications" else None,
                        Limit=50 if path == "/notifications" else None,
                    )
                except urllib.error.HTTPError as err:
                    bundle[key] = {"error": err.code}
            out["generators"][str(did)] = bundle

    if args.redact:
        out = json.loads(
            re.sub(
                r'("serialNumber"|"macAddress"|"address\d?"|"deviceIpAddress"):\s*"[^"]*"',
                r'\1: "REDACTED"',
                json.dumps(out),
            )
        )

    if args.out:
        args.out.mkdir(parents=True, exist_ok=True)
        target = args.out / "rehlko_capture.json"
        target.write_text(json.dumps(out, indent=2), encoding="utf-8")
        print(f"Wrote {target}", file=sys.stderr)
    else:
        counts = {
            gid: {k: (len(v) if isinstance(v, list) else "ok") for k, v in g.items()}
            for gid, g in out["generators"].items()
        }
        print(json.dumps({"account": me.get("id"), "generators": counts}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
