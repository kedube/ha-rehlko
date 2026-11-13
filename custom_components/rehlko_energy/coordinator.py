"""Polling coordinator: telemetry, feeds, change detection, and every write action."""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.exceptions import (
    ConfigEntryAuthFailed,
    HomeAssistantError,
    ServiceValidationError,
)
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.event import async_call_later
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import RehlkoApiError, RehlkoAuthError, RehlkoClient, RehlkoError
from .api.util import format_timestamp, humanize, parse_timestamp, slugify
from .const import (
    CONF_ACTIVE_SCAN_INTERVAL,
    CONF_FEED_INTERVAL,
    CONF_NOTIFICATION_LIMIT,
    CONF_SCAN_INTERVAL,
    DEFAULT_ACTIVE_SCAN_INTERVAL,
    DEFAULT_FEED_INTERVAL,
    DEFAULT_NOTIFICATION_LIMIT,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    EVENT_ALERT,
    EVENT_ALERT_CLEARED,
    EVENT_DEVICE_EVENT,
    EVENT_NOTIFICATION,
    EVENT_POWER,
    EXERCISE_DEFAULT_MINUTES,
    EXERCISE_MAX_MINUTES,
    EXERCISE_MIN_MINUTES,
    SLOW_REFRESH,
    STORAGE_KEY_SEEN,
    STORAGE_VERSION,
)
from .models import EMPTY_ENUMS, AccountData, GeneratorData

if TYPE_CHECKING:
    from . import RehlkoConfigEntry

_LOGGER = logging.getLogger(__name__)

MAX_SEEN = 400  # remembered item ids per feed
# A generator must be missing from this many consecutive successful account reads before its
# devices are removed, so one odd answer from the service cannot discard anyone's entities.
STALE_POLLS = 3
MAX_BURST = 25  # most items fired from one feed in one refresh (e.g. after downtime)
FOLLOW_UP_REFRESHES = (8, 25, 60)  # seconds after a write; the controller lags the cloud

FEED_DEVICE_EVENT = "event"
FEED_ALERT = "alert"
FEED_ALERT_CLEARED = "alert_cleared"
FEED_NOTIFICATION = "notification"
FEED_POWER = "power"

POWER_UTILITY_LOST = "utility_lost"
POWER_UTILITY_RESTORED = "utility_restored"
POWER_GENERATOR_STARTED = "generator_started"
POWER_GENERATOR_STOPPED = "generator_stopped"
POWER_TO_GENERATOR = "transferred_to_generator"
POWER_TO_UTILITY = "transferred_to_utility"
POWER_EVENT_TYPES = [
    POWER_UTILITY_LOST,
    POWER_UTILITY_RESTORED,
    POWER_GENERATOR_STARTED,
    POWER_GENERATOR_STOPPED,
    POWER_TO_GENERATOR,
    POWER_TO_UTILITY,
]


@dataclass(slots=True)
class FeedItem:
    """One new thing to announce: an activity entry, alert, notification or power change."""

    feed: str
    generator: GeneratorData
    item: dict[str, Any]
    event_type: str


def item_key(item: dict[str, Any]) -> str:
    if item.get("id") is not None:
        return str(item["id"])
    return f"{item.get('deviceEventId') or item.get('type')}|{item.get('timestamp')}"


def _sort_key(item: dict[str, Any]) -> float:
    ts = parse_timestamp(item.get("timestamp"))
    return ts.timestamp() if ts else 0.0


class SeenTracker:
    """Remembers which feed items were already announced, across restarts."""

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        self._store: Store[dict[str, Any]] = Store(
            hass, STORAGE_VERSION, f"{STORAGE_KEY_SEEN}.{entry_id}"
        )
        self._data: dict[str, dict[str, list[str]]] = {}

    async def async_load(self) -> None:
        self._data = await self._store.async_load() or {}

    async def async_remove(self) -> None:
        await self._store.async_remove()

    async def async_flush(self) -> None:
        """Write now. A reload within the save delay would otherwise re-announce items."""
        await self._store.async_save(self._data)

    def _save(self) -> None:
        self._store.async_delay_save(lambda: self._data, 10)

    def fresh(self, device_id: int, feed: str, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Items not seen before. The first sight of a feed only seeds it."""
        # Keep the newest window, including on the first poll. Comparing an unbounded
        # history with a bounded cache otherwise announces evicted old items forever.
        items = sorted(items, key=_sort_key, reverse=True)[:MAX_SEEN]
        bucket = self._data.setdefault(str(device_id), {})
        keys = list(dict.fromkeys(item_key(i) for i in items))
        if feed not in bucket:
            bucket[feed] = keys
            self._save()
            return []
        known = set(bucket[feed])
        fresh = [i for i in items if item_key(i) not in known]
        if fresh:
            bucket[feed] = list(dict.fromkeys(keys + bucket[feed]))[:MAX_SEEN]
            self._save()
        return fresh

    def active_diff(
        self, device_id: int, feed: str, items: list[dict[str, Any]]
    ) -> tuple[list[dict[str, Any]], list[str]]:
        """For a list of *currently active* items: (newly active items, cleared keys)."""
        bucket = self._data.setdefault(str(device_id), {})
        keys = [item_key(i) for i in items]
        first_sight = feed not in bucket
        before = set(bucket.get(feed, []))
        bucket[feed] = keys
        if set(keys) != before or first_sight:
            self._save()
        if first_sight:
            return [], []
        added = [i for i, k in zip(items, keys, strict=True) if k not in before]
        cleared = [k for k in before if k not in set(keys)]
        return added, cleared


class RehlkoCoordinator(DataUpdateCoordinator[AccountData]):
    """Owns the client for one account and everything polled from it."""

    config_entry: RehlkoConfigEntry

    def __init__(self, hass: HomeAssistant, entry: RehlkoConfigEntry, client: RehlkoClient) -> None:
        options = entry.options
        self._idle_interval = timedelta(
            seconds=options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        )
        self._active_interval = timedelta(
            seconds=options.get(CONF_ACTIVE_SCAN_INTERVAL, DEFAULT_ACTIVE_SCAN_INTERVAL)
        )
        self._feed_interval = timedelta(
            seconds=options.get(CONF_FEED_INTERVAL, DEFAULT_FEED_INTERVAL)
        )
        self._notification_limit = int(
            options.get(CONF_NOTIFICATION_LIMIT, DEFAULT_NOTIFICATION_LIMIT)
        )
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            # Not the entry's title: that is the account's email address, and this name is
            # written to the log.
            name=DOMAIN,
            update_interval=self._idle_interval,
            always_update=True,
        )
        self.client = client
        self.seen = SeenTracker(hass, entry.entry_id)
        self._last_feeds = 0.0
        self._last_slow = 0.0
        self._force_feeds: set[int] = set()
        self._feed_listeners: list[Callable[[FeedItem], None]] = []
        self._follow_ups: list[CALLBACK_TYPE] = []
        self._definitions: dict[tuple[int, str, str], Any] = {}
        self._notification_lock = asyncio.Lock()
        self._unreachable: set[int] = set()  # generators whose details call is failing
        self._absent: dict[int, int] = {}  # generator id -> consecutive polls it was missing

    # ------------------------------------------------------------------ lifecycle
    async def _async_setup(self) -> None:
        await self.seen.async_load()

    @callback
    def async_shutdown_follow_ups(self) -> None:
        for cancel in self._follow_ups:
            cancel()
        self._follow_ups.clear()

    @callback
    def async_add_feed_listener(self, listener: Callable[[FeedItem], None]) -> CALLBACK_TYPE:
        self._feed_listeners.append(listener)

        @callback
        def _remove() -> None:
            if listener in self._feed_listeners:
                self._feed_listeners.remove(listener)

        return _remove

    @property
    def longest_interval(self) -> timedelta:
        """The longest normal gap between two polls (for entities that integrate over time)."""
        return max(self._idle_interval, self._active_interval)

    def generator(self, device_id: int) -> GeneratorData:
        if self.data is None or device_id not in self.data.generators:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="unknown_generator",
                translation_placeholders={"device_id": str(device_id)},
            )
        return self.data.generators[device_id]

    # ------------------------------------------------------------------ polling
    async def _async_update_data(self) -> AccountData:
        previous = self.data
        try:
            homes = await self.client.get_homes()
        except RehlkoAuthError as err:
            raise _auth_failed(err) from err
        except RehlkoError as err:
            raise UpdateFailed(
                f"Rehlko service unavailable: {err}",
                translation_domain=DOMAIN,
                translation_key="unavailable",
                translation_placeholders={"message": str(err)},
            ) from err

        now = time.monotonic()
        was_active = previous is not None and any(g.is_active for g in previous.generators.values())
        feed_interval = self._feed_interval.total_seconds()
        if was_active:
            feed_interval = min(feed_interval, max(30.0, self._active_interval.total_seconds() * 2))
        feeds_due = now - self._last_feeds >= feed_interval
        slow_due = now - self._last_slow >= SLOW_REFRESH.total_seconds()

        generators: dict[int, GeneratorData] = {}
        forced = self._force_feeds
        self._force_feeds = set()
        for home in homes:
            for device in home.get("devices") or []:
                device_id = device.get("id")
                if device_id is None:
                    continue
                old = previous.generators.get(device_id) if previous else None
                gen = GeneratorData(
                    device_id=device_id, home=home, device=dict(device), details_available=False
                )
                if old is not None:
                    gen.details = old.details
                    gen.alerts = old.alerts
                    gen.events = old.events
                    gen.maintenance_notes = old.maintenance_notes
                    gen.notifications = old.notifications
                    gen.cell_plan = old.cell_plan
                    gen.details_updated = old.details_updated
                    gen.feeds_updated = old.feeds_updated
                generators[device_id] = gen

        self._async_remove_stale_devices(set(generators))
        results = await asyncio.gather(
            *(
                self._async_refresh_generator(
                    gen,
                    feeds=feeds_due or gen.device_id in forced or gen.feeds_updated is None,
                    slow=slow_due or gen.device_id in forced or gen.details_updated is None,
                )
                for gen in generators.values()
            ),
            return_exceptions=True,
        )
        for result in results:
            if isinstance(result, RehlkoAuthError):
                raise _auth_failed(result) from result
            if isinstance(result, BaseException) and not isinstance(result, RehlkoError):
                raise result
        me = previous.me if previous else {}
        settings = previous.notification_settings if previous else None
        if slow_due:
            me, settings = await self._async_refresh_account(me, settings)

        if feeds_due and all(
            gen.refreshed_feeds == {"events", "alerts", "notifications"}
            for gen in generators.values()
        ):
            self._last_feeds = now
        if slow_due:
            self._last_slow = now

        data = AccountData(
            me=me, homes=homes, generators=generators, notification_settings=settings
        )
        self._announce(previous, data)
        self.update_interval = (
            self._active_interval
            if any(g.is_active for g in generators.values())
            else self._idle_interval
        )
        return data

    @callback
    def _async_remove_stale_devices(self, present: set[int]) -> None:
        """Drop the devices of generators that have left the account."""
        registry = dr.async_get(self.hass)
        devices: dict[int, list[dr.DeviceEntry]] = {}
        for device in dr.async_entries_for_config_entry(registry, self.config_entry.entry_id):
            for domain, identifier in device.identifiers:
                base = identifier.split(":", 1)[0]
                if domain == DOMAIN and base.isdigit():
                    devices.setdefault(int(base), []).append(device)
        # An account that suddenly lists nothing is more likely a service fault than a sale.
        missing = set(devices) - present if present else set()
        self._absent = {gid: self._absent.get(gid, 0) + 1 for gid in missing}
        for generator_id, count in self._absent.items():
            if count < STALE_POLLS:
                continue
            for device in devices[generator_id]:
                _LOGGER.info("Removing %s: it is no longer on the account", device.name)
                registry.async_update_device(
                    device.id, remove_config_entry_id=self.config_entry.entry_id
                )
            self._unreachable.discard(generator_id)

    async def _async_refresh_account(
        self, me: dict[str, Any], settings: dict[str, Any] | None
    ) -> tuple[dict[str, Any], dict[str, Any] | None]:
        async with self._notification_lock:
            me_result, settings_result = await asyncio.gather(
                self.client.get_me(),
                self.client.get_notification_settings(),
                return_exceptions=True,
            )
        for result in (me_result, settings_result):
            if isinstance(result, RehlkoAuthError):
                raise _auth_failed(result) from result
            if isinstance(result, BaseException):
                _LOGGER.debug("Could not refresh the account profile: %s", result)
        if isinstance(me_result, dict):
            me = me_result
        if isinstance(settings_result, dict):
            settings = settings_result
        return me, settings

    async def _async_refresh_generator(
        self, gen: GeneratorData, *, feeds: bool, slow: bool
    ) -> None:
        client = self.client
        host = gen.source_host
        gen.details_available = False
        try:
            details = await client.get_device(gen.device_id, host)
        except RehlkoAuthError:
            raise
        except RehlkoError as err:
            if gen.device_id not in self._unreachable:
                self._unreachable.add(gen.device_id)
                _LOGGER.warning("Could not refresh %s: %s", gen.name, err)
        else:
            if gen.device_id in self._unreachable:
                self._unreachable.discard(gen.device_id)
                _LOGGER.info("%s is reporting again", gen.name)
            nested = details.get("device")
            gen.details = {k: v for k, v in details.items() if k != "device"}
            if isinstance(nested, dict):
                # The details call's copy of the device summary is the fresher one.
                gen.device = {**gen.device, **{k: v for k, v in nested.items() if v is not None}}
            gen.details_updated = dt_util.utcnow()
            gen.details_available = True

        if feeds:
            events, alerts, notifications = await asyncio.gather(
                client.get_events(gen.device_id, host),
                client.get_alerts(gen.device_id, host),
                client.get_notifications(device_id=gen.device_id, limit=self._notification_limit),
                return_exceptions=True,
            )
            for result in (events, alerts, notifications):
                if isinstance(result, RehlkoAuthError):
                    raise result
                if isinstance(result, BaseException):
                    _LOGGER.debug("Could not refresh a feed of %s: %s", gen.name, result)
            if isinstance(events, list):
                gen.events = sorted(events, key=_sort_key, reverse=True)
                gen.refreshed_feeds.add("events")
            if isinstance(alerts, list):
                gen.alerts = sorted(alerts, key=_sort_key, reverse=True)
                gen.refreshed_feeds.add("alerts")
            if isinstance(notifications, list):
                gen.notifications = sorted(notifications, key=_sort_key, reverse=True)
                gen.refreshed_feeds.add("notifications")
            if len(gen.refreshed_feeds) == 3:
                gen.feeds_updated = dt_util.utcnow()

        if slow:
            notes = await asyncio.gather(
                client.get_maintenance_notes(gen.device_id), return_exceptions=True
            )
            if isinstance(notes[0], RehlkoAuthError):
                raise notes[0]
            if isinstance(notes[0], list):
                gen.maintenance_notes = sorted(notes[0], key=_sort_key, reverse=True)
            connection = gen.get("connectionType")
            if (
                connection in ("Cellular", "KohlerCellKit")
                or gen.get("cellularKitOnline") is not None
            ):
                try:
                    gen.cell_plan = await client.get_cell_plan(gen.device_id)
                except RehlkoAuthError:
                    raise
                except RehlkoError as err:
                    _LOGGER.debug("No cell plan for %s: %s", gen.name, err)

    # ------------------------------------------------------------------ announcing
    def _announce(self, previous: AccountData | None, data: AccountData) -> None:
        for gen in data.generators.values():
            items: list[FeedItem] = []
            events = (
                self.seen.fresh(gen.device_id, "events", gen.events)
                if "events" in gen.refreshed_feeds
                else []
            )
            for item in self._burst(events):
                items.append(
                    FeedItem(FEED_DEVICE_EVENT, gen, item, slugify(item.get("level") or "none"))
                )
            added, cleared = (
                self.seen.active_diff(gen.device_id, "alerts", gen.alerts)
                if "alerts" in gen.refreshed_feeds
                else ([], [])
            )
            for item in self._burst(added):
                items.append(FeedItem(FEED_ALERT, gen, item, "raised"))
            for key in cleared:
                items.append(FeedItem(FEED_ALERT_CLEARED, gen, {"id": key}, "cleared"))
            notifications = (
                self.seen.fresh(gen.device_id, "notifications", gen.notifications)
                if "notifications" in gen.refreshed_feeds
                else []
            )
            for item in self._burst(notifications):
                items.append(
                    FeedItem(FEED_NOTIFICATION, gen, item, slugify(item.get("type") or "notice"))
                )
            old = previous.generators.get(gen.device_id) if previous else None
            if (
                old is not None
                and old.details_available
                and gen.details_available
                and old.is_connected
                and gen.is_connected
                and old.details
                and gen.details
            ):
                items.extend(self._power_changes(old, gen))
            for feed_item in items:
                self._fire(feed_item)

    @staticmethod
    def _burst(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        ordered = sorted(items, key=_sort_key)
        if len(ordered) > MAX_BURST:
            _LOGGER.debug("Announcing only the newest %s of %s items", MAX_BURST, len(ordered))
            ordered = ordered[-MAX_BURST:]
        return ordered

    @staticmethod
    def _power_changes(old: GeneratorData, new: GeneratorData) -> list[FeedItem]:
        out: list[FeedItem] = []

        def add(kind: str) -> None:
            out.append(
                FeedItem(
                    FEED_POWER,
                    new,
                    {
                        "timestamp": dt_util.utcnow().isoformat(),
                        "utility_voltage": new.details.get("utilityVoltageV"),
                        "generator_voltage": new.details.get("generatorVoltageAvgV"),
                        "power_source": new.details.get("powerSource"),
                        "engine_state": new.engine_state,
                        "status": new.status,
                    },
                    kind,
                )
            )

        if old.utility_present is True and new.utility_present is False:
            add(POWER_UTILITY_LOST)
        elif old.utility_present is False and new.utility_present is True:
            add(POWER_UTILITY_RESTORED)
        if not old.is_running and new.is_running:
            add(POWER_GENERATOR_STARTED)
        elif old.is_running and not new.is_running:
            add(POWER_GENERATOR_STOPPED)
        if not old.on_generator_power and new.on_generator_power:
            add(POWER_TO_GENERATOR)
        elif (
            old.on_generator_power
            and not new.on_generator_power
            and (new.details.get("powerSource") == "Utility")
        ):
            add(POWER_TO_UTILITY)
        return out

    def ha_device_id(self, gen: GeneratorData) -> str | None:
        device = dr.async_get(self.hass).async_get_device(
            identifiers={(DOMAIN, str(gen.device_id))}
        )
        return device.id if device else None

    def _fire(self, feed_item: FeedItem) -> None:
        gen, item = feed_item.generator, feed_item.item
        base = {
            "device_id": self.ha_device_id(gen),
            "generator_id": gen.device_id,
            "serial_number": gen.serial_number,
            "generator_name": gen.name,
            "type": feed_item.event_type,
        }
        if feed_item.feed == FEED_DEVICE_EVENT:
            bus_event, payload = EVENT_DEVICE_EVENT, {**base, **describe_event(item)}
        elif feed_item.feed == FEED_ALERT:
            bus_event, payload = EVENT_ALERT, {**base, **describe_event(item)}
        elif feed_item.feed == FEED_ALERT_CLEARED:
            bus_event, payload = EVENT_ALERT_CLEARED, {**base, "id": item.get("id")}
        elif feed_item.feed == FEED_NOTIFICATION:
            bus_event, payload = EVENT_NOTIFICATION, {**base, **describe_notification(item)}
        else:
            bus_event, payload = EVENT_POWER, {**base, **item}
        self.hass.bus.async_fire(bus_event, payload)
        for listener in list(self._feed_listeners):
            try:
                listener(feed_item)
            except Exception:  # a broken listener must not stop the others
                _LOGGER.exception("Feed listener failed")

    # ------------------------------------------------------------------ writes
    async def _async_call(self, coro: Any) -> Any:
        try:
            return await coro
        except RehlkoAuthError as err:
            self.config_entry.async_start_reauth(self.hass)
            raise HomeAssistantError(
                translation_domain=DOMAIN, translation_key="auth_failed"
            ) from err
        except RehlkoApiError as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="api_error",
                translation_placeholders={"message": err.message, "status": str(err.status)},
            ) from err
        except RehlkoError as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="unavailable",
                translation_placeholders={"message": str(err)},
            ) from err

    async def _async_after_write(self, device_id: int | None = None) -> None:
        if device_id is not None:
            self._force_feeds.add(device_id)
        await self.async_refresh()
        self.async_shutdown_follow_ups()

        @callback
        def _again(_now: datetime) -> None:
            if device_id is not None:
                self._force_feeds.add(device_id)
            self.hass.async_create_task(self.async_request_refresh())

        for delay in FOLLOW_UP_REFRESHES:
            self._follow_ups.append(async_call_later(self.hass, delay, _again))

    def _require_online(self, gen: GeneratorData) -> None:
        if not self.last_update_success or not gen.details_available or not gen.is_connected:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="offline",
                translation_placeholders={"name": gen.name},
            )

    async def async_start_exercise(self, device_id: int, mode: str | None = None) -> None:
        gen = self.generator(device_id)
        self._require_online(gen)
        if gen.e_stop_engaged:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="e_stop",
                translation_placeholders={"name": gen.name},
            )
        if not gen.ready_to_run:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="not_ready",
                translation_placeholders={"name": gen.name, "status": humanize(gen.status) or "?"},
            )
        mode = (
            mode
            or (gen.exercise.get("mode") if gen.exercise.get("mode") not in EMPTY_ENUMS else None)
            or "Unloaded"
        )
        await self._async_call(self.client.start_exercise(device_id, mode))
        await self._async_after_write(device_id)

    async def async_stop_exercise(self, device_id: int) -> None:
        gen = self.generator(device_id)
        self._require_online(gen)
        await self._async_call(self.client.stop_exercise(device_id))
        await self._async_after_write(device_id)

    async def async_set_exercise_schedule(
        self,
        device_id: int,
        *,
        frequency: str | None = None,
        mode: str | None = None,
        duration_minutes: int | None = None,
        next_start: datetime | None = None,
    ) -> None:
        gen = self.generator(device_id)
        self._require_online(gen)
        if not gen.supports_exercise_scheduling:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="no_scheduling",
                translation_placeholders={"name": gen.name},
            )
        current = gen.exercise
        frequency = frequency or _set_or(current.get("frequency"), "EveryOtherWeek")
        mode = mode or _set_or(current.get("mode"), "Unloaded")
        duration = int(
            duration_minutes or current.get("durationMinutes") or EXERCISE_DEFAULT_MINUTES
        )
        duration = max(EXERCISE_MIN_MINUTES, min(EXERCISE_MAX_MINUTES, duration))
        reference = current.get("nextStartTimestamp")
        if next_start is not None:
            next_value: str | None = format_timestamp(
                next_start, like=reference, site_tz=dt_util.get_default_time_zone()
            )
        else:
            next_value = reference
        await self._async_call(
            self.client.set_exercise_schedule(
                device_id,
                frequency=frequency,
                mode=mode,
                duration_minutes=duration,
                next_start=next_value,
            )
        )
        await self._async_after_write(device_id)

    async def async_delete_exercise_schedule(self, device_id: int) -> None:
        gen = self.generator(device_id)
        self._require_online(gen)
        await self._async_call(self.client.delete_exercise_schedule(device_id))
        await self._async_after_write(device_id)

    async def async_add_maintenance_note(self, device_id: int, contents: str) -> None:
        self.generator(device_id)
        contents = contents.strip()
        if not contents:
            raise ServiceValidationError(translation_domain=DOMAIN, translation_key="empty_note")
        await self._async_call(self.client.add_maintenance_note(device_id, contents))
        await self._async_after_write(device_id)

    async def async_sync_controller_clock(
        self, device_id: int, when: datetime | None = None
    ) -> None:
        gen = self.generator(device_id)
        self._require_online(gen)
        when = when or dt_util.now()
        value = format_timestamp(
            when,
            like=gen.details.get("controllerClockTimestamp"),
            site_tz=dt_util.get_default_time_zone(),
        )
        await self._async_call(self.client.set_controller_clock(device_id, value))
        await self._async_after_write(device_id)

    async def async_set_peripheral_value(
        self, device_id: int, definition_id: Any, value: Any
    ) -> None:
        gen = self.generator(device_id)
        self._require_online(gen)
        param = next(
            (
                p
                for _, p in gen.peripheral_parameters()
                if str(p.get("definitionId")) == str(definition_id)
            ),
            None,
        )
        if param is not None and param.get("isReadOnly"):
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="read_only",
                translation_placeholders={"name": str(param.get("displayName") or definition_id)},
            )
        await self._async_call(self.client.set_peripheral_value(device_id, definition_id, value))
        await self._async_after_write(device_id)

    async def async_rename_peripheral(self, device_id: int, definition_id: Any, name: str) -> None:
        self.generator(device_id)
        name = name.strip()
        if not name:
            raise ServiceValidationError(translation_domain=DOMAIN, translation_key="empty_name")
        await self._async_call(self.client.rename_peripheral(device_id, definition_id, name))
        await self._async_after_write(device_id)

    async def async_update_device(self, device_id: int, **changes: Any) -> None:
        """PUT the device with its current settings plus `changes` (API field names)."""
        gen = self.generator(device_id)
        body = {
            "displayName": gen.device.get("displayName"),
            "address": gen.device.get("address"),
            "connectionType": gen.get("connectionType"),
            "autoFirmwareUpdateEnabled": gen.details.get("autoFirmwareUpdateEnabled"),
        }
        progress = gen.install_progress
        if progress.get("type") is not None:
            body["installProgressType"] = progress.get("type")
            body["completedInstallProgressSteps"] = progress.get("completedSteps")
        body.update(changes)
        await self._async_call(self.client.update_device(device_id, body))
        await self._async_after_write(device_id)

    async def async_set_notification_setting(self, key: str, enabled: bool) -> None:
        # Every POST replaces the full object. Serialize the read/merge/write so two
        # switches (or automations) cannot undo each other's changes.
        async with self._notification_lock:
            settings = dict((self.data.notification_settings if self.data else None) or {})
            if not settings:
                settings = await self._async_call(self.client.get_notification_settings()) or {}
            settings[key] = enabled
            await self._async_call(self.client.set_notification_settings(settings))
            if self.data is not None:
                self.data.notification_settings = settings
                self.async_update_listeners()
        self._last_slow = 0.0  # re-read on the next poll to confirm
        await self.async_request_refresh()

    async def async_get_parameter_definitions(self, device_id: int, kind: str, serial: str) -> Any:
        self.generator(device_id)
        key = (device_id, kind, serial)
        if key not in self._definitions:
            self._definitions[key] = await self._async_call(
                self.client.get_parameter_definitions(device_id, kind, serial)
            )
        return self._definitions[key]

    async def async_refresh_everything(self) -> None:
        if self.data:
            self._force_feeds.update(self.data.generators)
        self._last_slow = 0.0
        await self.async_refresh()


def _set_or(value: Any, default: str) -> str:
    return default if value in EMPTY_ENUMS else str(value)


def _auth_failed(err: RehlkoAuthError) -> ConfigEntryAuthFailed:
    return ConfigEntryAuthFailed(str(err), translation_domain=DOMAIN, translation_key="auth_failed")


def describe_event(item: dict[str, Any]) -> dict[str, Any]:
    """A device event/alert as flat, readable event data."""
    code = item.get("deviceEventId") or item.get("event")
    return {
        "id": item.get("id"),
        "code": code,
        "name": item.get("name") or humanize(code),
        "level": item.get("level"),
        "event": item.get("event"),
        "event_int_id": item.get("deviceEventIntId"),
        "fmi": item.get("fmi"),
        "parameter_id": item.get("parameterId"),
        "parameter": item.get("parameter"),
        "event_type": item.get("type"),
        "timestamp": item.get("timestamp"),
        "is_critical_fault": item.get("isCriticalFault"),
        "can_remote_reset_fault": item.get("canRemoteResetFault"),
    }


def describe_notification(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": item.get("id"),
        "notification_type": item.get("type"),
        "tag": item.get("tag"),
        "message": item.get("message"),
        "timestamp": item.get("timestamp"),
        "cta_text": item.get("ctaText"),
        "cta_link": item.get("ctaLink"),
        "is_e_stop_event": item.get("isEStopEvent"),
    }
