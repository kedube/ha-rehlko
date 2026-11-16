"""Text: the generator's name in the app, and writable text peripheral parameters."""

from __future__ import annotations

from collections.abc import Iterator
from functools import partial
from typing import Any

from homeassistant.components.text import TextEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import RehlkoConfigEntry
from .const import DOMAIN
from .coordinator import RehlkoCoordinator
from .entity import EntityFactory, RehlkoEntity, async_discover_entities
from .peripherals import PeripheralMixin, writable_params

PARALLEL_UPDATES = 1


async def async_setup_entry(
    hass: HomeAssistant,
    entry: RehlkoConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data

    def candidates() -> Iterator[tuple[str, EntityFactory]]:
        for device_id, gen in coordinator.data.generators.items():
            yield f"{device_id}-generator_name", partial(GeneratorNameText, coordinator, device_id)
            for kind, param in writable_params(gen, (str,)):
                definition_id = param["definitionId"]
                yield (
                    f"{device_id}-peripheral-text-{definition_id}",
                    partial(PeripheralText, coordinator, device_id, kind, definition_id),
                )

    async_discover_entities(entry, async_add_entities, candidates)


class GeneratorNameText(RehlkoEntity, TextEntity):
    """The generator's display name as the app shows it (`PUT /devices/{id}`)."""

    _attr_translation_key = "generator_name"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_native_min = 1
    _attr_native_max = 64

    def __init__(self, coordinator: RehlkoCoordinator, device_id: int) -> None:
        super().__init__(coordinator, device_id, "generator_name")

    @property
    def native_value(self) -> str | None:
        gen = self.gen
        return gen.device.get("displayName") if gen else None

    async def async_set_value(self, value: str) -> None:
        name = value.strip()
        if not name:
            raise ServiceValidationError(translation_domain=DOMAIN, translation_key="empty_name")
        await self.coordinator.async_update_device(self._device_id, displayName=name)


class PeripheralText(PeripheralMixin, RehlkoEntity, TextEntity):
    _attr_entity_category = EntityCategory.CONFIG
    _attr_native_max = 255

    def __init__(
        self, coordinator: RehlkoCoordinator, device_id: int, kind: str, definition_id: Any
    ) -> None:
        super().__init__(coordinator, device_id, f"peripheral-text-{definition_id}")
        self._setup_peripheral(kind, definition_id)

    @property
    def native_value(self) -> str | None:
        value = (self._param() or {}).get("value")
        return value if isinstance(value, str) else None

    async def async_set_value(self, value: str) -> None:
        await self._write(value)
