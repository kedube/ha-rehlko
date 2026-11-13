"""Selects: the exercise schedule's mode and frequency."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import RehlkoConfigEntry
from .api.util import slugify
from .const import EXERCISE_FREQUENCIES, EXERCISE_MODES
from .coordinator import RehlkoCoordinator
from .entity import RehlkoEntity, async_discover_generators

PARALLEL_UPDATES = 1


@dataclass(frozen=True, kw_only=True)
class RehlkoSelectDescription(SelectEntityDescription):
    field: str
    wire_values: tuple[str, ...]


SELECTS = (
    RehlkoSelectDescription(
        key="exercise_mode",
        translation_key="exercise_mode",
        entity_category=EntityCategory.CONFIG,
        field="mode",
        wire_values=EXERCISE_MODES,
    ),
    RehlkoSelectDescription(
        key="exercise_frequency",
        translation_key="exercise_frequency",
        entity_category=EntityCategory.CONFIG,
        field="frequency",
        wire_values=EXERCISE_FREQUENCIES,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: RehlkoConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_discover_generators(
        entry,
        async_add_entities,
        lambda gen: (ExerciseSelect(coordinator, gen.device_id, desc) for desc in SELECTS),
        lambda gen: "exercise" in gen.details and gen.supports_exercise_scheduling,
    )


class ExerciseSelect(RehlkoEntity, SelectEntity):
    entity_description: RehlkoSelectDescription

    def __init__(
        self, coordinator: RehlkoCoordinator, device_id: int, description: RehlkoSelectDescription
    ) -> None:
        super().__init__(coordinator, device_id, description.key)
        self.entity_description = description
        self._by_slug = {slugify(v): v for v in description.wire_values}
        self._attr_options = list(self._by_slug)

    @property
    def available(self) -> bool:
        return super().available and bool(self.gen and self.gen.is_connected)

    @property
    def current_option(self) -> str | None:
        gen = self.gen
        value = gen.exercise.get(self.entity_description.field) if gen else None
        slug = slugify(value) if value else None
        return slug if slug in self._by_slug else None

    async def async_select_option(self, option: str) -> None:
        await self.coordinator.async_set_exercise_schedule(
            self._device_id, **{self.entity_description.field: self._by_slug[option]}
        )
