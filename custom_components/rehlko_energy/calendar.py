"""Calendar: scheduled exercises (projected from the schedule), the last run, maintenance due."""

from __future__ import annotations

import calendar as pycal
from datetime import date, datetime, timedelta

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util

from . import RehlkoConfigEntry
from .api.util import humanize, parse_timestamp, slugify
from .const import EXERCISE_DEFAULT_MINUTES
from .coordinator import RehlkoCoordinator
from .entity import RehlkoEntity, async_discover_generators, async_entity_texts
from .models import EMPTY_ENUMS, GeneratorData
from .texts import (
    CALENDAR_DESCRIPTION,
    CALENDAR_DESCRIPTION_PATH,
    CALENDAR_SUMMARY,
    CALENDAR_SUMMARY_PATH,
    EXERCISE_MODE_PATH,
    Texts,
    text,
)

PARALLEL_UPDATES = 0
MAX_OCCURRENCES = 120
LAST_EXERCISE = "last-exercise"


def _add_month(when: datetime, anchor_day: int | None = None) -> datetime:
    year, month = (when.year + 1, 1) if when.month == 12 else (when.year, when.month + 1)
    day = min(anchor_day or when.day, pycal.monthrange(year, month)[1])
    return when.replace(year=year, month=month, day=day)


def _step(when: datetime, frequency: str | None, anchor_day: int | None = None) -> datetime | None:
    if frequency == "Weekly":
        return when + timedelta(days=7)
    if frequency == "EveryOtherWeek":
        return when + timedelta(days=14)
    if frequency == "Monthly":
        return _add_month(when, anchor_day)
    return None


def exercise_events(
    gen: GeneratorData, start: datetime, end: datetime, texts: Texts | None = None
) -> list[CalendarEvent]:
    """Events between `start` and `end`, titled in `texts`' language (English without it)."""

    def summary_text(key: str) -> str:
        return text(texts, CALENDAR_SUMMARY_PATH, CALENDAR_SUMMARY, key)

    def description_text(key: str) -> str:
        return text(texts, CALENDAR_DESCRIPTION_PATH, CALENDAR_DESCRIPTION, key)

    tz = dt_util.get_default_time_zone()
    ex = gen.exercise
    events: list[CalendarEvent] = []
    minutes = int(ex.get("durationMinutes") or EXERCISE_DEFAULT_MINUTES)
    mode = None
    if ex.get("mode") not in EMPTY_ENUMS:
        mode = (texts or {}).get(f"{EXERCISE_MODE_PATH}.{slugify(ex['mode'])}") or humanize(
            ex["mode"]
        )
    summary = f"{summary_text('exercise')} ({mode})" if mode else summary_text("exercise")

    last_start = parse_timestamp(ex.get("lastStartTimestamp"), tz)
    last_end = parse_timestamp(ex.get("lastEndTimestamp"), tz)
    if last_start and (last_end is None or last_end <= last_start):
        last_end = last_start + timedelta(minutes=minutes)
    if last_start and last_end and last_end > start and last_start < end:
        events.append(
            CalendarEvent(
                start=last_start,
                end=last_end,
                summary=summary_text("last_exercise"),
                description=description_text("last_exercise"),
                uid=f"{gen.device_id}-{LAST_EXERCISE}",
            )
        )

    next_start = parse_timestamp(ex.get("nextStartTimestamp"), tz)
    if next_start is not None and gen.has_schedule:
        # Recur at the site's wall-clock time, including when the API used UTC.
        occurrence: datetime | None = next_start.astimezone(tz)
        anchor_day = occurrence.day
        count = 0
        while occurrence is not None and occurrence < end and count < MAX_OCCURRENCES:
            finish = occurrence + timedelta(minutes=minutes)
            if finish > start:
                events.append(
                    CalendarEvent(
                        start=occurrence,
                        end=finish,
                        summary=summary,
                        description=description_text("scheduled" if count == 0 else "projected"),
                        uid=f"{gen.device_id}-exercise-{occurrence.isoformat()}",
                    )
                )
            occurrence = _step(occurrence, ex.get("frequency"), anchor_day)
            count += 1

    due = parse_timestamp(gen.device.get("nextMaintenanceTimestamp"), tz)
    if due is not None:
        day = dt_util.as_local(due).date()
        if (
            dt_util.start_of_local_day(day + timedelta(days=1)) > start
            and dt_util.start_of_local_day(day) < end
        ):
            events.append(
                CalendarEvent(
                    start=day,
                    end=day + timedelta(days=1),
                    summary=summary_text("maintenance_due"),
                    description=description_text("maintenance_due"),
                    uid=f"{gen.device_id}-maintenance-{day.isoformat()}",
                )
            )
    return sorted(events, key=lambda e: _as_dt(e.start))


def _as_dt(value: date | datetime) -> datetime:
    if isinstance(value, datetime):
        return value
    return dt_util.start_of_local_day(value)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: RehlkoConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_discover_generators(
        entry, async_add_entities, lambda gen: [ExerciseCalendar(coordinator, gen.device_id)]
    )


class ExerciseCalendar(RehlkoEntity, CalendarEntity):
    _attr_translation_key = "schedule"

    def __init__(self, coordinator: RehlkoCoordinator, device_id: int) -> None:
        super().__init__(coordinator, device_id, "calendar")
        self._texts: Texts | None = None

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self._texts = await async_entity_texts(self.hass)

    @property
    def event(self) -> CalendarEvent | None:
        gen = self.gen
        if gen is None:
            return None
        now = dt_util.now()
        last = f"{gen.device_id}-{LAST_EXERCISE}"
        for event in exercise_events(
            gen, now - timedelta(hours=2), now + timedelta(days=400), self._texts
        ):
            if _as_dt(event.end) >= now and event.uid != last:
                return event
        return None

    async def async_get_events(
        self, hass: HomeAssistant, start_date: datetime, end_date: datetime
    ) -> list[CalendarEvent]:
        gen = self.gen
        return exercise_events(gen, start_date, end_date, self._texts) if gen else []
