"""Numbers: exercise duration, and writable numeric load-module / PIM parameters."""

from __future__ import annotations

from typing import Any

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.const import EntityCategory, UnitOfTime
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import RehlkoConfigEntry
from .const import EXERCISE_MAX_MINUTES, EXERCISE_MIN_MINUTES
from .coordinator import RehlkoCoordinator
from .entity import RehlkoEntity
from .peripherals import PeripheralMixin, writable_params

PARALLEL_UPDATES = 1


async def async_setup_entry(
    hass: HomeAssistant,
    entry: RehlkoConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    created: set[str] = set()

    @callback
    def _discover() -> None:
        new: list[NumberEntity] = []
        for device_id, gen in coordinator.data.generators.items():
            if "exercise" in gen.details and gen.supports_exercise_scheduling:
                uid = f"{device_id}-exercise_duration"
                if uid not in created:
                    created.add(uid)
                    new.append(ExerciseDurationNumber(coordinator, device_id))
            for kind, param in writable_params(gen, (int, float)):
                uid = f"{device_id}-peripheral-number-{param['definitionId']}"
                if uid not in created:
                    created.add(uid)
                    new.append(
                        PeripheralNumber(coordinator, device_id, kind, param["definitionId"])
                    )
        if new:
            async_add_entities(new)

    _discover()
    entry.async_on_unload(coordinator.async_add_listener(_discover))


class ExerciseDurationNumber(RehlkoEntity, NumberEntity):
    _attr_translation_key = "exercise_duration"
    _attr_entity_category = EntityCategory.CONFIG
    _attr_native_min_value = EXERCISE_MIN_MINUTES
    _attr_native_max_value = EXERCISE_MAX_MINUTES
    _attr_native_step = 1
    _attr_mode = NumberMode.BOX
    _attr_native_unit_of_measurement = UnitOfTime.MINUTES

    def __init__(self, coordinator: RehlkoCoordinator, device_id: int) -> None:
        super().__init__(coordinator, device_id, "exercise_duration")

    @property
    def available(self) -> bool:
        return super().available and bool(self.gen and self.gen.is_connected)

    @property
    def native_value(self) -> float | None:
        gen = self.gen
        value = gen.exercise.get("durationMinutes") if gen else None
        return float(value) if isinstance(value, (int, float)) else None

    async def async_set_native_value(self, value: float) -> None:
        await self.coordinator.async_set_exercise_schedule(
            self._device_id, duration_minutes=int(value)
        )


class PeripheralNumber(PeripheralMixin, RehlkoEntity, NumberEntity):
    _attr_entity_category = EntityCategory.CONFIG
    _attr_mode = NumberMode.BOX
    _attr_native_min_value = -1_000_000
    _attr_native_max_value = 1_000_000
    _attr_native_step = 1

    def __init__(
        self, coordinator: RehlkoCoordinator, device_id: int, kind: str, definition_id: Any
    ) -> None:
        super().__init__(coordinator, device_id, f"peripheral-number-{definition_id}")
        self._setup_peripheral(kind, definition_id)
        if isinstance((self._param() or {}).get("value"), float):
            self._attr_native_step = 0.1

    @property
    def native_value(self) -> float | None:
        value = (self._param() or {}).get("value")
        return (
            float(value)
            if isinstance(value, (int, float)) and not isinstance(value, bool)
            else None
        )

    async def async_set_native_value(self, value: float) -> None:
        current = (self._param() or {}).get("value")
        await self._write(int(value) if isinstance(current, int) and value.is_integer() else value)
