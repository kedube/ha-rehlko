"""Polling coordinator: telemetry, feeds, change detection, and every write action."""

from __future__ import annotations

import asyncio
import functools
import hashlib
import heapq
import json
import logging
import time
from collections.abc import Callable, Coroutine
from dataclasses import dataclass
from datetime import datetime, timedelta, tzinfo
from typing import TYPE_CHECKING, Any, NamedTuple

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

MAX_SEEN = 400  # the newest items of one answer that are compared with what was seen
# Ids remembered per feed: twice what one answer is compared on, so an item that leaves the
# answer (newer ones arrived) is still known if it comes back (newer ones were deleted).
MAX_REMEMBERED = 2 * MAX_SEEN
SEEN_SAVE_DELAY = 1  # seconds; written before a crash or power cut could repeat announcements
SEEN_FEEDS = ("events", "alerts", "notifications")
SEEN_META = "meta"  # beside a generator's id lists: how each feed was last read
META_FIELDS = ("window", "since")
# A generator must be missing from this many consecutive successful account reads before its
# devices are removed, so one odd answer from the service cannot discard anyone's entities.
STALE_POLLS = 3
MAX_BURST = 25  # most items fired from one feed in one refresh (e.g. after downtime)
FOLLOW_UP_REFRESHES = (8, 25, 60)  # seconds after a write; the controller lags the cloud
ALL_FEEDS = frozenset({"events", "alerts", "notifications"})
# A failed feed read is tried again at the next poll, then after doubling gaps (capped here)
# until it is back on the feed interval.
MAX_RETRY_DOUBLINGS = 10

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


# What tells apart two items that came without an id. Not fields that may change after the
# fact: the item would come back as a new one.
_IDENTIFYING = (
    "deviceEventId",
    "deviceEventIntId",
    "event",
    "name",
    "level",
    "fmi",
    "parameterId",
    "tag",
    "message",
)


def _has_id(item: dict[str, Any]) -> bool:
    return item.get("id") not in (None, "")


def legacy_item_key(item: dict[str, Any]) -> str:
    """How earlier versions keyed an item without an id: two of a type at one time shared it."""
    return f"{item.get('deviceEventId') or item.get('type')}|{item.get('timestamp')}"


def item_key(item: dict[str, Any]) -> str:
    if _has_id(item):
        ident = item["id"]
        # The same number, however the service writes it (7, 7.0).
        if isinstance(ident, float) and ident.is_integer():
            ident = int(ident)
        return str(ident)
    fields = json.dumps([item.get(name) for name in _IDENTIFYING], default=str)
    return f"{legacy_item_key(item)}|{hashlib.sha256(fields.encode()).hexdigest()[:12]}"


@functools.lru_cache(maxsize=4096)
def _parsed(text: str, tz: tzinfo) -> float | None:
    # A feed's items come back at every poll and are ordered more than once in each: each
    # time is parsed once.
    ts = parse_timestamp(text, tz)
    return ts.timestamp() if ts else None


def _stamp(item: dict[str, Any]) -> float | None:
    """When an item happened (POSIX time). A time without an offset is the site's."""
    value = item.get("timestamp")
    return _parsed(value, dt_util.get_default_time_zone()) if isinstance(value, str) else None


def _sort_key(item: dict[str, Any]) -> float:
    stamp = _stamp(item)
    return 0.0 if stamp is None else stamp


class _Entry(NamedTuple):
    stamp: float | None
    key: str
    item: dict[str, Any]


def _order(entry: _Entry) -> tuple[float, str]:
    # Equal times are ordered by key, so the same items make the cut however the service
    # orders its answer: otherwise one could drop out, be forgotten, return and be announced.
    return (0.0 if entry.stamp is None else entry.stamp, entry.key)


def _newest(items: list[dict[str, Any]]) -> list[_Entry]:
    """Each item once (its newest copy), newest first, at most MAX_SEEN of them."""
    unique: dict[str, _Entry] = {}
    for item in items:
        entry = _Entry(_stamp(item), item_key(item), item)
        kept = unique.get(entry.key)
        if kept is None or _order(entry) > _order(kept):
            unique[entry.key] = entry
    return heapq.nlargest(MAX_SEEN, unique.values(), key=_order)


def _remembered(entry: _Entry, known: set[str], legacy: bool) -> bool:
    if entry.key in known:
        return True
    # A feed recorded by an earlier version knows an item without an id by its legacy key.
    return legacy and not _has_id(entry.item) and legacy_item_key(entry.item) in known


def _usable(stored: Any) -> dict[str, dict[str, Any]]:
    """What can be used of the stored record.

    A malformed part is left out and its feed starts over: its first answer is remembered, not
    announced. Otherwise it would fail every poll until someone deleted the file.
    """
    out: dict[str, dict[str, Any]] = {}
    damaged = stored is not None and not isinstance(stored, dict)
    for device_id, bucket in stored.items() if isinstance(stored, dict) else ():
        if not isinstance(bucket, dict):
            damaged = True
            continue
        clean: dict[str, Any] = {}
        for feed in SEEN_FEEDS:
            keys = bucket.get(feed)
            if isinstance(keys, list) and all(isinstance(k, str) for k in keys):
                clean[feed] = keys
            elif feed in bucket:
                damaged = True
        meta = bucket.get(SEEN_META, {})
        if not isinstance(meta, dict):
            damaged, meta = True, {}
        clean[SEEN_META] = {}
        for feed, record in meta.items():
            if feed not in clean:
                continue  # nothing to describe (or a feed this version does not read)
            window = record.get("window", 0) if isinstance(record, dict) else None
            since = record.get("since") if isinstance(record, dict) else None
            if type(window) is int and window >= 0 and type(since) in (type(None), int, float):
                clean[SEEN_META][feed] = {k: v for k, v in record.items() if k in META_FIELDS}
            else:
                damaged = True  # the feed is read as one recorded by an earlier version
        out[device_id] = clean
    if damaged:
        _LOGGER.warning(
            "Part of the stored record of announced activity could not be read and starts "
            "over; what the affected feeds list at their next read is not announced"
        )
    return out


class SeenTracker:
    """Remembers which feed items were already announced, across restarts.

    Stored per generator: each feed's remembered ids, newest first, and under `meta` how each
    feed was last read. Earlier versions read the id lists and ignore `meta`.
    """

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        self._store: Store[dict[str, Any]] = Store(
            hass, STORAGE_VERSION, f"{STORAGE_KEY_SEEN}.{entry_id}"
        )
        self._data: dict[str, dict[str, Any]] = {}
        self.closed = False

    async def async_load(self) -> None:
        self._data = _usable(await self._store.async_load())

    async def async_remove(self) -> None:
        await self._store.async_remove()

    async def async_close(self) -> None:
        """Write now, and record nothing more (at unload).

        A reload within the save delay would otherwise announce items again. So would a poll of
        the unloaded entry still under way (started by an action): the reloaded entry has read
        the record already, and would announce the same items itself.
        """
        self.closed = True
        await self._store.async_save(self._data)

    def _save(self) -> None:
        if not self.closed:
            self._store.async_delay_save(lambda: self._data, SEEN_SAVE_DELAY)

    def device_ids(self) -> set[int]:
        """The generators anything is remembered for."""
        return {int(device_id) for device_id in self._data if device_id.isdigit()}

    def forget(self, device_id: int) -> None:
        """Drop what was seen of a generator that has left the account."""
        if not self.closed and self._data.pop(str(device_id), None) is not None:
            self._save()

    def _bucket(self, device_id: int) -> tuple[dict[str, Any], dict[str, Any]]:
        bucket = self._data.setdefault(str(device_id), {})
        return bucket, bucket.setdefault(SEEN_META, {})

    def fresh(
        self, device_id: int, feed: str, items: list[dict[str, Any]], *, window: int = 0
    ) -> list[dict[str, Any]]:
        """Items not seen before, newest first. The first sight of a feed only seeds it.

        Anything not seen before is news, whatever its time says: a controller whose clock was
        reset dates new entries in the past. Older items are history only when the answer can
        reach further back than before: `window` (how many items were asked for; 0 when the
        service decides) has grown, or the feed was empty when first read.
        """
        if self.closed:
            return []
        entries = _newest(items)
        keys = [entry.key for entry in entries]
        bucket, meta = self._bucket(device_id)
        last: dict[str, Any] | None = meta.get(feed)
        record: dict[str, Any] = {"window": window}
        if feed not in bucket or (last is None and not bucket[feed]):
            bucket[feed] = keys
            if not keys:
                record["since"] = dt_util.utcnow().timestamp()
            meta[feed] = record
            self._save()
            return []
        known = set(bucket[feed])
        unseen = [entry for entry in entries if not _remembered(entry, known, last is None)]
        # A larger limit, or the first answer since an update from a version that did not
        # record one: what is older than everything already seen in this answer is history it
        # did not show before.
        reaches_further = last is None or window > last.get("window", 0)
        new_keys = {entry.key for entry in unseen}
        floor = min(
            (e.stamp for e in entries if e.key not in new_keys and e.stamp is not None),
            default=None,
        )
        # The feed was empty when first read: what is dated before that is a backlog it only
        # now shows (a new generator's, or the empty answer was a fault), not news.
        since = last.get("since") if last else None
        news = [
            entry.item
            for entry in unseen
            if not (
                reaches_further
                and (entry.stamp is None or (floor is not None and entry.stamp < floor))
            )
            and not (since is not None and entry.stamp is not None and entry.stamp < since)
        ]
        bucket[feed] = list(dict.fromkeys(keys + bucket[feed]))[:MAX_REMEMBERED]
        if since is not None and not bucket[feed]:
            record["since"] = since
        if unseen or record != last:
            self._save()
        meta[feed] = record
        return news

    def active_diff(
        self, device_id: int, feed: str, items: list[dict[str, Any]]
    ) -> tuple[list[dict[str, Any]], list[str]]:
        """For a list of *currently active* items: (newly active items, cleared keys)."""
        if self.closed:
            return [], []
        current: dict[str, dict[str, Any]] = {}
        for item in items:
            current.setdefault(item_key(item), item)
        bucket, meta = self._bucket(device_id)
        first_sight = feed not in bucket
        before = set(bucket.get(feed, []))
        if not first_sight and feed not in meta:
            # Recorded by an earlier version: an item without an id is under its legacy key.
            renamed = {
                key: legacy_item_key(item) for key, item in current.items() if not _has_id(item)
            }
            matched = before & set(renamed.values())
            before = (before - matched) | {key for key, old in renamed.items() if old in matched}
        changed = first_sight or feed not in meta or set(current) != before
        bucket[feed] = list(current)
        meta[feed] = {}
        if changed:
            self._save()
        if first_sight:
            return [], []
        added = [item for key, item in current.items() if key not in before]
        cleared = [key for key in before if key not in current]
        return added, cleared


def _read_failed(result: object, what: str) -> bool:
    """Whether one of several reads made together failed.

    A failed sign-in or a cancellation is raised. The service failing is expected and only
    noted; anything else is a bug, logged as an error with its traceback, so a feed that stops
    updating says why.
    """
    if isinstance(result, (RehlkoAuthError, asyncio.CancelledError)):
        raise result
    if isinstance(result, RehlkoError):
        _LOGGER.debug("Could not refresh %s: %s", what, result)
    elif isinstance(result, BaseException):
        _LOGGER.error("Unexpected error refreshing %s", what, exc_info=result)
    else:
        return False
    return True


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
        # None until the first refresh, and again to force a read. Never 0.0: the monotonic clock
        # counts from boot, so on a host that has just started, 0.0 is moments ago and nothing
        # would look due.
        self._last_slow: float | None = None
        # Per generator: when its feeds were last read (monotonic), how many reads in a row
        # failed, and whether its slow data has been read since setup. One generator's failing
        # feed never makes another generator's feeds due.
        self._feeds_tried: dict[int, float] = {}
        self._feed_failures: dict[int, int] = {}
        self._slow_read: set[int] = set()
        self._force_feeds: set[int] = set()
        self._feed_listeners: list[Callable[[FeedItem], None]] = []
        self._follow_ups: list[CALLBACK_TYPE] = []
        self._definitions: dict[tuple[int, str, str], Any] = {}
        self._notification_lock = asyncio.Lock()
        self._settings_writes = 0  # notification-setting writes so far (see _async_update_data)
        self._device_locks: dict[int, asyncio.Lock] = {}  # one device PUT (and refresh) at a time
        self._last_good: dict[int, GeneratorData] = {}  # last connected reading with details
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
        poll = (self._active_interval if was_active else self._idle_interval).total_seconds()
        feed_interval = self._feed_interval.total_seconds()
        if was_active:
            feed_interval = min(feed_interval, max(30.0, self._active_interval.total_seconds() * 2))
        slow_due = self._last_slow is None or now - self._last_slow >= SLOW_REFRESH.total_seconds()

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
        self._forget_departed(set(generators))
        # Due by each generator's own record: never read, forced by a write, or its interval
        # is up. Not by what the data lacks: a generator whose details or a feed keep failing
        # would otherwise be read in full at every poll.
        feeds = {
            device_id: device_id in forced or self._feeds_due(device_id, now, feed_interval, poll)
            for device_id in generators
        }
        slow = {
            device_id: slow_due or device_id in forced or device_id not in self._slow_read
            for device_id in generators
        }
        me = previous.me if previous else {}
        settings = previous.notification_settings if previous else None
        writes = self._settings_writes
        refreshes: list[Coroutine[Any, Any, Any]] = [
            self._async_refresh_generator(gen, feeds=feeds[device_id], slow=slow[device_id])
            for device_id, gen in generators.items()
        ]
        if slow_due:
            # Alongside the generators: the account's reads do not depend on theirs.
            refreshes.append(self._async_refresh_account(me, settings))
        results = await asyncio.gather(*refreshes, return_exceptions=True)
        for result in results:
            if isinstance(result, RehlkoAuthError):
                raise _auth_failed(result) from result
            if isinstance(result, BaseException) and not isinstance(result, RehlkoError):
                raise result
        if slow_due and isinstance(results[-1], tuple):
            me, settings = results[-1]
        if self._settings_writes != writes:
            # A setting was written while this poll ran: what it holds may predate that. Keep
            # the written one, and leave `_last_slow` as the write left it (read it again).
            settings = self.data.notification_settings if self.data else settings
        elif slow_due:
            self._last_slow = now
        for device_id, gen in generators.items():
            if slow[device_id]:
                self._slow_read.add(device_id)
            if feeds[device_id]:
                self._feeds_tried[device_id] = now
                if gen.refreshed_feeds >= ALL_FEEDS:
                    self._feed_failures.pop(device_id, None)
                else:
                    self._feed_failures[device_id] = self._feed_failures.get(device_id, 0) + 1

        data = AccountData(
            me=me, homes=homes, generators=generators, notification_settings=settings
        )
        if items := self._announce(previous, data):
            # Fired once the coordinator has published `data` (it does so without yielding
            # after this returns), so listeners and event entities see the states the items
            # describe, not the previous poll's.
            self.hass.loop.call_soon(self._fire_all, items)
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
        # A generator with no devices left (removed by hand) can still have a seen record.
        tracked = set(devices) | self.seen.device_ids()
        missing = tracked - present if present else set()
        self._absent = {gid: self._absent.get(gid, 0) + 1 for gid in missing}
        for generator_id, count in self._absent.items():
            if count < STALE_POLLS:
                continue
            self.seen.forget(generator_id)
            for device in devices.get(generator_id, []):
                _LOGGER.info("Removing %s: it is no longer on the account", device.name)
                entry_id = self.config_entry.entry_id
                # Newer Home Assistant gives every device one config entry (`config_entry_id`).
                # Older versions share a device between two accounts that both list the
                # generator, and there it is only detached from this account.
                if hasattr(device, "config_entry_id") or device.config_entries <= {entry_id}:
                    registry.async_remove_device(device.id)
                else:
                    registry.async_update_device(device.id, remove_config_entry_id=entry_id)
            self._unreachable.discard(generator_id)

    def _forget_departed(self, present: set[int]) -> None:
        """Drop the schedules of generators the account no longer lists."""
        for schedule in (self._feeds_tried, self._feed_failures):
            for device_id in set(schedule) - present:
                del schedule[device_id]
        self._slow_read &= present
        for device_id in set(self._last_good) - present:
            del self._last_good[device_id]

    def _feeds_due(self, device_id: int, now: float, interval: float, poll: float) -> bool:
        """Whether a generator's activity log, alerts and notifications are due a read."""
        tried = self._feeds_tried.get(device_id)
        if tried is None:
            return True
        if failures := self._feed_failures.get(device_id, 0):
            # Tried again at the next poll, then after doubling gaps until it is back on the
            # feed interval: a feed that keeps failing costs what a working one does.
            interval = min(interval, poll * 2 ** min(failures - 1, MAX_RETRY_DOUBLINGS))
        return now - tried >= interval

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
            _read_failed(result, "the account profile")
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
                _read_failed(result, f"a feed of {gen.name}")
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
            if not _read_failed(notes[0], f"the maintenance notes of {gen.name}"):
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
    def _announce(self, previous: AccountData | None, data: AccountData) -> list[FeedItem]:
        """What is new since the last poll; the seen-store is updated as it is worked out."""
        # Unloaded while this poll ran, the closed seen-store reports no feed item: the reloaded
        # entry announces them. A power change is still announced; the reloaded entry has no
        # earlier reading to find it with.
        items: list[FeedItem] = []
        for gen in data.generators.values():
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
            old = previous.generators.get(gen.device_id) if previous else None
            was_active = {item_key(alert): alert for alert in old.alerts} if old else {}
            for key in cleared:
                alert = was_active.get(key) or {"id": key}
                items.append(FeedItem(FEED_ALERT_CLEARED, gen, alert, "cleared"))
            notifications = (
                self.seen.fresh(
                    gen.device_id,
                    "notifications",
                    gen.notifications,
                    window=self._notification_limit,
                )
                if "notifications" in gen.refreshed_feeds
                else []
            )
            for item in self._burst(notifications):
                items.append(
                    FeedItem(FEED_NOTIFICATION, gen, item, slugify(item.get("type") or "notice"))
                )
            # Against the last good reading: a poll without one in between (a failed read, or
            # the router down with the utility) must not hide the outage itself.
            if gen.details_available and gen.is_connected and gen.details:
                if (base := self._last_good.get(gen.device_id)) is not None:
                    items.extend(self._power_changes(base, gen))
                self._last_good[gen.device_id] = gen
        return items

    @callback
    def _fire_all(self, items: list[FeedItem]) -> None:
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
        # Among this entry's own devices: newer Home Assistant lets another entry hold a
        # device with the same identifier, and deprecates the registry-wide lookup.
        identifier = (DOMAIN, str(gen.device_id))
        for device in dr.async_entries_for_config_entry(
            dr.async_get(self.hass), self.config_entry.entry_id
        ):
            if identifier in device.identifiers:
                return device.id
        return None

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
            bus_event, payload = EVENT_ALERT_CLEARED, {**base, **describe_event(item)}
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
            # The entry's own task: cancelled when it unloads.
            self.config_entry.async_create_background_task(
                self.hass, self.async_request_refresh(), f"{DOMAIN} follow-up refresh"
            )

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
        kind, param = next(
            (
                (k, p)
                for k, p in gen.peripheral_parameters()
                if str(p.get("definitionId")) == str(definition_id)
            ),
            (None, None),
        )
        if kind is not None and param is not None:
            name = str(param.get("displayName") or definition_id)
            if param.get("isReadOnly"):
                raise HomeAssistantError(
                    translation_domain=DOMAIN,
                    translation_key="read_only",
                    translation_placeholders={"name": name},
                )
            # The service still lists a detached module's settings; the panel locks them too.
            if not gen.peripheral_connected(kind):
                if kind == "loadShed":
                    raise HomeAssistantError(
                        translation_domain=DOMAIN,
                        translation_key="load_module_disconnected",
                        translation_placeholders={"name": name},
                    )
                raise HomeAssistantError(
                    translation_domain=DOMAIN,
                    translation_key="pim_disconnected",
                    translation_placeholders={"name": name},
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
        # The PUT replaces every field: the next one is built after this one is read back.
        async with self._device_locks.setdefault(device_id, asyncio.Lock()):
            await self._async_put_device(device_id, changes)

    async def _async_put_device(self, device_id: int, changes: dict[str, Any]) -> None:
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
            self._settings_writes += 1
            if self.data is not None:
                self.data.notification_settings = settings
                self.async_update_listeners()
        self._last_slow = None  # re-read on the next poll to confirm
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
        self._last_slow = None
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
