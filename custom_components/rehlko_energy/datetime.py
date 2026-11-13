"""Datetime: when the next scheduled exercise starts (where the controller allows choosing)."""

from __future__ import annotations

from datetime import datetime

from homeassistant.components.datetime import DateTimeEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util

from . import RehlkoConfigEntry
from .api.util import parse_timestamp
from .coordinator import RehlkoCoordinator
from .entity import RehlkoEntity, async_discover_generators

PARALLEL_UPDATES = 1


async def async_setup_entry(
    hass: HomeAssistant,
    entry: RehlkoConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_discover_generators(
        entry,
        async_add_entities,
        lambda gen: [NextExerciseDateTime(coordinator, gen.device_id)],
        lambda gen: "exercise" in gen.details and gen.supports_exercise_scheduling,
    )


class NextExerciseDateTime(RehlkoEntity, DateTimeEntity):
    _attr_translation_key = "next_exercise_start"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: RehlkoCoordinator, device_id: int) -> None:
        super().__init__(coordinator, device_id, "next_exercise_start")

    @property
    def available(self) -> bool:
        gen = self.gen
        # The app hides the date/time picker unless the controller supports choosing it.
        return super().available and bool(
            gen and gen.is_connected and gen.supports_next_exercise_datetime
        )

    @property
    def native_value(self) -> datetime | None:
        gen = self.gen
        if gen is None:
            return None
        return parse_timestamp(
            gen.exercise.get("nextStartTimestamp"), dt_util.get_default_time_zone()
        )

    async def async_set_value(self, value: datetime) -> None:
        await self.coordinator.async_set_exercise_schedule(self._device_id, next_start=value)
