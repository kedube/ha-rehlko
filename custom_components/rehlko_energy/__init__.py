"""The Rehlko Energy Management integration (Rehlko / Kohler home standby generators)."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.typing import ConfigType

from .api import AppCredentials, OktaAuth, RehlkoClient
from .const import (
    API_BASE_URL,
    CONF_API_KEY,
    CONF_BASE_URL,
    CONF_CLIENT_ID,
    CONF_CLIENT_SECRET,
    CONF_REFRESH_TOKEN,
    DOMAIN,
    OKTA_SCOPES,
    OKTA_TOKEN_URL,
)
from .coordinator import RehlkoCoordinator
from .services import async_setup_services
from .sidebar import async_setup_sidebar

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.CALENDAR,
    Platform.DATETIME,
    Platform.EVENT,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.SENSOR,
    Platform.SWITCH,
    Platform.TEXT,
    Platform.UPDATE,
]

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

type RehlkoConfigEntry = ConfigEntry[RehlkoCoordinator]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Once per run: the domain's services and the sidebar panel's plumbing."""
    async_setup_services(hass)
    await async_setup_sidebar(hass)
    return True


def build_client(hass: HomeAssistant, entry: ConfigEntry) -> RehlkoClient:
    session = async_get_clientsession(hass)
    data = entry.data
    app = AppCredentials(data[CONF_CLIENT_ID], data[CONF_CLIENT_SECRET], data[CONF_API_KEY])

    def _persist(token: str) -> None:
        if entry.data.get(CONF_REFRESH_TOKEN) != token:
            hass.config_entries.async_update_entry(
                entry, data={**entry.data, CONF_REFRESH_TOKEN: token}
            )

    auth = OktaAuth(
        session,
        app,
        token_url=OKTA_TOKEN_URL,
        scopes=OKTA_SCOPES,
        username=data[CONF_USERNAME],
        password=data.get(CONF_PASSWORD),
        refresh_token=data.get(CONF_REFRESH_TOKEN),
        on_refresh_token=_persist,
    )
    return RehlkoClient(session, auth, base_url=data.get(CONF_BASE_URL) or API_BASE_URL)


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """1.1 -> 1.2: generator entities' unique IDs gain the account, `{entry id}-{old id}`.

    Without it a generator shared with two configured accounts gave both accounts' entities
    the same IDs, and Home Assistant refused the second set.
    """
    if entry.version > 1:
        return False  # written by a newer release
    if entry.minor_version < 2:
        prefix = f"{entry.entry_id}-"

        @callback
        def _with_account(entity: er.RegistryEntry) -> dict[str, str] | None:
            if entity.unique_id.startswith(("account-", prefix)):
                return None
            return {"new_unique_id": f"{prefix}{entity.unique_id}"}

        await er.async_migrate_entries(hass, entry.entry_id, _with_account)
        hass.config_entries.async_update_entry(entry, minor_version=2)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: RehlkoConfigEntry) -> bool:
    coordinator = RehlkoCoordinator(hass, entry, build_client(hass, entry))
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    options_at_setup = dict(entry.options)

    async def _options_changed(hass: HomeAssistant, changed: ConfigEntry) -> None:
        # Token rotation also updates the entry; only option changes need a reload.
        if dict(changed.options) != options_at_setup:
            await hass.config_entries.async_reload(changed.entry_id)

    entry.async_on_unload(entry.add_update_listener(_options_changed))
    entry.async_on_unload(coordinator.async_shutdown_follow_ups)
    entry.async_on_unload(coordinator.seen.async_flush)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: RehlkoConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_remove_entry(hass: HomeAssistant, entry: RehlkoConfigEntry) -> None:
    """Forget which feed items were announced for this account."""
    from .coordinator import SeenTracker

    await SeenTracker(hass, entry.entry_id).async_remove()


async def async_remove_config_entry_device(
    hass: HomeAssistant, entry: RehlkoConfigEntry, device: dr.DeviceEntry
) -> bool:
    """Allow removing devices for generators that left the account."""
    coordinator = entry.runtime_data
    known = {
        str(device_id) for device_id in (coordinator.data.generators if coordinator.data else {})
    }
    for domain, identifier in device.identifiers:
        if domain != DOMAIN:
            continue
        base = identifier.split(":", 1)[0]
        if base in known or identifier == f"account:{entry.entry_id}":
            return False
    return True
