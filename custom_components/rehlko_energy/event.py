"""Event entities: activity log, alerts, app notifications, and derived power events.

The same items are also fired on the bus (`rehlko_energy_device_event`, `_alert`,
`_alert_cleared`, `_notification`, `_power`) for automations that prefer event triggers.
"""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.event import EventEntity, EventEntityDescription
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import RehlkoConfigEntry
from .api import vocabulary as V
from .api.util import slugify
from .coordinator import (
    FEED_ALERT,
    FEED_ALERT_CLEARED,
    FEED_DEVICE_EVENT,
    FEED_NOTIFICATION,
    FEED_POWER,
    POWER_EVENT_TYPES,
    FeedItem,
    RehlkoCoordinator,
    describe_event,
    describe_notification,
)
from .entity import RehlkoEntity, async_discover_generators

PARALLEL_UPDATES = 0


def _slugs(values: tuple[str, ...], *extra: str) -> list[str]:
    out: list[str] = []
    for value in (*values, *extra):
        slug = slugify(value)
        if slug and slug not in out:
            out.append(slug)
    return out


@dataclass(frozen=True, kw_only=True)
class RehlkoEventDescription(EventEntityDescription):
    feeds: tuple[str, ...]
    fallback: str


EVENTS = (
    RehlkoEventDescription(
        key="activity",
        translation_key="activity",
        feeds=(FEED_DEVICE_EVENT,),
        event_types=_slugs(V.DEVICE_EVENT_LEVEL),
        fallback="notice",
    ),
    RehlkoEventDescription(
        key="alerts",
        translation_key="alerts",
        feeds=(FEED_ALERT, FEED_ALERT_CLEARED),
        event_types=["raised", "cleared"],
        fallback="raised",
    ),
    RehlkoEventDescription(
        key="notifications",
        translation_key="notifications",
        feeds=(FEED_NOTIFICATION,),
        event_types=_slugs(V.NOTIFICATION_TYPE, "Notice"),
        fallback="notice",
    ),
    RehlkoEventDescription(
        key="power",
        translation_key="power",
        feeds=(FEED_POWER,),
        event_types=list(POWER_EVENT_TYPES),
        fallback=POWER_EVENT_TYPES[0],
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
        lambda gen: (RehlkoEvent(coordinator, gen.device_id, desc) for desc in EVENTS),
    )


class RehlkoEvent(RehlkoEntity, EventEntity):
    entity_description: RehlkoEventDescription

    def __init__(
        self, coordinator: RehlkoCoordinator, device_id: int, description: RehlkoEventDescription
    ) -> None:
        super().__init__(coordinator, device_id, f"event-{description.key}")
        self.entity_description = description

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(self.coordinator.async_add_feed_listener(self._on_feed))

    @callback
    def _on_feed(self, feed_item: FeedItem) -> None:
        if feed_item.generator.device_id != self._device_id:
            return
        if feed_item.feed not in self.entity_description.feeds:
            return
        event_type = feed_item.event_type
        if event_type not in (self.entity_description.event_types or []):
            event_type = self.entity_description.fallback
        if feed_item.feed in (FEED_DEVICE_EVENT, FEED_ALERT):
            attributes = describe_event(feed_item.item)
        elif feed_item.feed == FEED_NOTIFICATION:
            attributes = describe_notification(feed_item.item)
        else:
            attributes = dict(feed_item.item)
        self._trigger_event(event_type, {k: v for k, v in attributes.items() if v is not None})
        self.async_write_ha_state()
