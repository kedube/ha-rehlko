"""The Generator sidebar panel: serving it, showing it, and taking it away.

The front end lives in `frontend/` and is built into `www/rehlko-energy-panel.js`. The panel
shows while any enabled entry has the sidebar option on (the default), whether or not that
entry has finished loading, so a reload never makes it blink.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from homeassistant.components import frontend, panel_custom
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import SIGNAL_CONFIG_ENTRY_CHANGED
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.util.hass_dict import HassKey

from ..const import CONF_SIDEBAR_PANEL, DEFAULT_SIDEBAR_PANEL, DOMAIN
from .commands import async_register_commands

__all__ = ["async_setup_sidebar", "async_sync_sidebar"]

_LOGGER = logging.getLogger(__name__)

URL_PATH = "rehlko-energy"
ELEMENT = "rehlko-energy-panel"
STATIC_URL = "/rehlko_energy_static/rehlko-energy-panel.js"
BUNDLE = Path(__file__).parent.parent / "www" / "rehlko-energy-panel.js"
ICON = "mdi:home-lightning-bolt"

# Home Assistant shows a custom panel's sidebar title as given, so it is chosen here from the
# server's language. One entry per language in `translations/` (a test keeps them in step).
TITLES = {
    "en": "Generator",
    "de": "Generator",
    "es": "Generador",
    "fr": "Génératrice",
    "it": "Generatore",
    "ja": "発電機",
    "nl": "Generator",
    "pl": "Agregat",
    "pt-BR": "Gerador",
    "zh-Hans": "发电机",
}
# Exact tags only: `zh-Hant` must not fall through to the Simplified Chinese title.
_LANGUAGE_ALIASES = {"pt": "pt-BR", "pt-PT": "pt-BR", "zh": "zh-Hans", "zh-CN": "zh-Hans"}


def sidebar_title(language: str | None) -> str:
    """The panel's sidebar title for a Home Assistant language tag such as `es-419`."""
    tag = language or "en"
    for candidate in (tag, _LANGUAGE_ALIASES.get(tag), tag.split("-")[0]):
        if candidate in TITLES:
            return TITLES[candidate]
    return TITLES["en"]


@dataclass
class SidebarState:
    version: str | None = None
    served: bool = False
    shown: bool = False
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)


DATA_SIDEBAR: HassKey[SidebarState] = HassKey(f"{DOMAIN}_sidebar")


def _bundle_version() -> str | None:
    try:
        return hashlib.sha256(BUNDLE.read_bytes()).hexdigest()[:12]
    except OSError:
        return None


async def async_setup_sidebar(hass: HomeAssistant) -> None:
    """Once per run: the websocket API, the bundle's URL, and keeping the panel in sync."""
    if DATA_SIDEBAR in hass.data:
        return
    state = hass.data[DATA_SIDEBAR] = SidebarState()
    async_register_commands(hass)
    state.version = await hass.async_add_executor_job(_bundle_version)
    if state.version is None:
        _LOGGER.warning("The sidebar panel's bundle is missing: %s", BUNDLE)
    elif getattr(hass, "http", None) is not None:
        # Registered once per run (aiohttp cannot remove a route). Cached freely: the URL
        # carries the bundle's digest, so a new build gets a new URL.
        await hass.http.async_register_static_paths(
            [StaticPathConfig(STATIC_URL, str(BUNDLE), cache_headers=True)]
        )
        state.served = True

    @callback
    def _entry_changed(_change: Any, entry: Any) -> None:
        if entry.domain == DOMAIN:
            hass.async_create_task(async_sync_sidebar(hass))

    async_dispatcher_connect(hass, SIGNAL_CONFIG_ENTRY_CHANGED, _entry_changed)
    await async_sync_sidebar(hass)


def _wanted(hass: HomeAssistant) -> bool:
    return any(
        entry.disabled_by is None and entry.options.get(CONF_SIDEBAR_PANEL, DEFAULT_SIDEBAR_PANEL)
        for entry in hass.config_entries.async_entries(DOMAIN)
    )


async def async_sync_sidebar(hass: HomeAssistant) -> None:
    """Show the panel if an entry wants it, remove it if none does (idempotent)."""
    state = hass.data.get(DATA_SIDEBAR)
    if state is None or not state.served:
        return
    async with state.lock:
        wanted = _wanted(hass)
        if wanted == state.shown:
            return
        if wanted:
            await panel_custom.async_register_panel(
                hass,
                frontend_url_path=URL_PATH,
                webcomponent_name=ELEMENT,
                sidebar_title=sidebar_title(hass.config.language),
                sidebar_icon=ICON,
                module_url=f"{STATIC_URL}?v={state.version}",
                config={"version": state.version},
                require_admin=True,
            )
        else:
            frontend.async_remove_panel(hass, URL_PATH, warn_if_unknown=False)
        state.shown = wanted
