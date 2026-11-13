"""Buttons: start/stop an exercise, sync the controller clock, refresh."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import RehlkoConfigEntry
from .coordinator import RehlkoCoordinator
from .entity import RehlkoEntity, async_discover_generators
from .models import GeneratorData

PARALLEL_UPDATES = 1


@dataclass(frozen=True, kw_only=True)
class RehlkoButtonDescription(ButtonEntityDescription):
    press_fn: Callable[[RehlkoCoordinator, int], Awaitable[None]]
    available_fn: Callable[[GeneratorData], bool] = lambda g: True


BUTTONS: tuple[RehlkoButtonDescription, ...] = (
    RehlkoButtonDescription(
        key="start_exercise",
        translation_key="start_exercise",
        press_fn=lambda c, d: c.async_start_exercise(d),
        available_fn=lambda g: g.is_connected and g.supports_exercise_scheduling,
    ),
    RehlkoButtonDescription(
        key="stop_exercise",
        translation_key="stop_exercise",
        press_fn=lambda c, d: c.async_stop_exercise(d),
        available_fn=lambda g: g.is_connected,
    ),
    RehlkoButtonDescription(
        key="sync_controller_clock",
        translation_key="sync_controller_clock",
        entity_category=EntityCategory.CONFIG,
        press_fn=lambda c, d: c.async_sync_controller_clock(d),
        available_fn=lambda g: g.is_connected,
    ),
    RehlkoButtonDescription(
        key="refresh",
        translation_key="refresh",
        entity_category=EntityCategory.DIAGNOSTIC,
        press_fn=lambda c, d: c.async_refresh_everything(),
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
        lambda gen: (RehlkoButton(coordinator, gen.device_id, desc) for desc in BUTTONS),
    )


class RehlkoButton(RehlkoEntity, ButtonEntity):
    entity_description: RehlkoButtonDescription

    def __init__(
        self, coordinator: RehlkoCoordinator, device_id: int, description: RehlkoButtonDescription
    ) -> None:
        super().__init__(coordinator, device_id, description.key)
        self.entity_description = description

    @property
    def available(self) -> bool:
        gen = self.gen
        return super().available and gen is not None and self.entity_description.available_fn(gen)

    async def async_press(self) -> None:
        await self.entity_description.press_fn(self.coordinator, self._device_id)
