"""The app's own credentials: the set built into the integration, or an entry's own."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.rehlko_energy import app_credentials
from custom_components.rehlko_energy.api import AppCredentials
from custom_components.rehlko_energy.app_credentials import (
    app_credentials_for,
    builtin_app_credentials,
    stored_app_credentials,
)
from custom_components.rehlko_energy.const import DOMAIN

ROOT = Path(__file__).resolve().parent.parent
OWN = {"client_id": "own-client", "client_secret": "own-secret", "api_key": "own-key"}


@pytest.mark.real_app_credentials
def test_the_integration_carries_a_complete_set(builtin_app) -> None:
    """The one test that looks at the real set. It shows none of it."""
    complete = all(
        isinstance(value, str) and value and value == value.strip()
        for value in (builtin_app.client_id, builtin_app.client_secret, builtin_app.api_key)
    )
    assert complete, "app_credentials.BUILTIN needs a client ID, a client secret and an API key"
    assert builtin_app is app_credentials.BUILTIN


def test_nothing_else_has_to_be_installed_for_them() -> None:
    manifest = json.loads(
        (ROOT / "custom_components" / "rehlko_energy" / "manifest.json").read_text()
    )
    assert manifest["requirements"] == []


def test_an_entrys_own_set_comes_first(builtin_app) -> None:
    assert builtin_app_credentials() == builtin_app
    assert app_credentials_for({}) == builtin_app
    assert app_credentials_for(OWN) == AppCredentials("own-client", "own-secret", "own-key")
    # Two of three is not a set.
    partial = {key: value for key, value in OWN.items() if key != "api_key"}
    assert stored_app_credentials(partial) is None
    assert app_credentials_for(partial) == builtin_app
    assert app_credentials.without_app_credentials({"username": "u", **OWN}) == {"username": "u"}


def entry_with(hass, data):
    entry = MockConfigEntry(domain=DOMAIN, title="Test account", unique_id="owner", data=data)
    entry.add_to_hass(hass)
    return entry


async def test_setup_signs_in_with_the_built_in_set(
    hass, client, builtin_app, enable_custom_integrations
) -> None:
    entry = entry_with(hass, {"username": "owner@example.com"})
    build = MagicMock(return_value=client)
    with patch("custom_components.rehlko_energy.build_client", build):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    assert build.call_args.args[2] == builtin_app
    assert entry.data == {"username": "owner@example.com"}

    from custom_components.rehlko_energy.diagnostics import async_get_config_entry_diagnostics

    diagnostics = await async_get_config_entry_diagnostics(hass, entry)
    assert diagnostics["api"]["app_credentials"] == "built_in"
    # The set itself is not in what a user might share.
    dumped = json.dumps(diagnostics, default=str)
    for value in (builtin_app.client_id, builtin_app.client_secret, builtin_app.api_key):
        assert value not in dumped


async def test_setup_signs_in_with_an_entrys_own_set(
    hass, client, enable_custom_integrations
) -> None:
    entry = entry_with(hass, {"username": "owner@example.com", **OWN})
    build = MagicMock(return_value=client)
    with patch("custom_components.rehlko_energy.build_client", build):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    assert build.call_args.args[2] == AppCredentials("own-client", "own-secret", "own-key")
    assert {key: entry.data[key] for key in OWN} == OWN

    from custom_components.rehlko_energy.diagnostics import async_get_config_entry_diagnostics

    diagnostics = await async_get_config_entry_diagnostics(hass, entry)
    assert diagnostics["api"]["app_credentials"] == "stored"
    dumped = json.dumps(diagnostics, default=str)
    assert "own-secret" not in dumped
    assert "own-key" not in dumped


async def test_setup_drops_a_saved_copy_of_the_built_in_set(
    hass, client, builtin_app, enable_custom_integrations
) -> None:
    """Entries made before the integration carried a set hold a copy of the same values."""
    copy = {
        "client_id": builtin_app.client_id,
        "client_secret": builtin_app.client_secret,
        "api_key": builtin_app.api_key,
    }
    entry = entry_with(hass, {"username": "owner@example.com", "password": "pw", **copy})
    with patch("custom_components.rehlko_energy.build_client", return_value=client):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    assert entry.data == {"username": "owner@example.com", "password": "pw"}
