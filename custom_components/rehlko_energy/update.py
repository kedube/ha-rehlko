"""Update entity: the controller firmware the service reports (installation is the dealer's or
the automatic-update setting's job; this entity only shows availability)."""

from __future__ import annotations

from homeassistant.components.update import UpdateDeviceClass, UpdateEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util

from . import RehlkoConfigEntry
from .api.util import parse_timestamp
from .coordinator import RehlkoCoordinator
from .entity import RehlkoEntity, async_discover_generators, async_entity_texts
from .texts import FIRMWARE_SUMMARY, FIRMWARE_SUMMARY_PATH, Texts, text

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: RehlkoConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_discover_generators(
        entry,
        async_add_entities,
        lambda gen: [FirmwareUpdate(coordinator, gen.device_id)],
        lambda gen: bool(gen.device.get("currentFirmware") or gen.device.get("firmwareVersion")),
    )


class FirmwareUpdate(RehlkoEntity, UpdateEntity):
    _attr_translation_key = "firmware"
    _attr_device_class = UpdateDeviceClass.FIRMWARE
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: RehlkoCoordinator, device_id: int) -> None:
        super().__init__(coordinator, device_id, "firmware")
        self._texts: Texts | None = None

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self._texts = await async_entity_texts(self.hass)

    def _text(self, key: str, **placeholders: str) -> str:
        template = text(self._texts, FIRMWARE_SUMMARY_PATH, FIRMWARE_SUMMARY, key)
        try:
            return template.format(**placeholders)
        except (KeyError, IndexError, ValueError):
            return FIRMWARE_SUMMARY[key].format(**placeholders)

    @property
    def installed_version(self) -> str | None:
        gen = self.gen
        if gen is None:
            return None
        return gen.device.get("firmwareVersion") or gen.device.get("currentFirmware")

    @property
    def latest_version(self) -> str | None:
        gen = self.gen
        if gen is None:
            return None
        update = gen.firmware_update
        if update.get("canBeUpdated") and (
            update.get("versionName") or update.get("versionNumber")
        ):
            return str(update.get("versionName") or update.get("versionNumber"))
        return self.installed_version

    @property
    def release_summary(self) -> str | None:
        gen = self.gen
        update = gen.firmware_update if gen else {}
        if not update.get("canBeUpdated"):
            return None
        parts = []
        if update.get("releaseDate"):
            parts.append(self._text("released", date=str(update["releaseDate"])[:10]))
        scheduled = gen.details.get("scheduledFirmwareUpdateTimestamp") if gen else None
        if scheduled:
            when = parse_timestamp(scheduled, dt_util.get_default_time_zone())
            shown = dt_util.as_local(when).strftime("%Y-%m-%d %H:%M") if when else str(scheduled)
            parts.append(self._text("scheduled", date=shown))
        if gen and gen.details.get("autoFirmwareUpdateEnabled") is False:
            parts.append(self._text("auto_update_off"))
        return " ".join(parts)[:255] or None
