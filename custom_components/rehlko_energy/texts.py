"""Text the integration renders itself: calendar events and the firmware release summary.

Home Assistant translates entity names and states in the browser, but a calendar event's title
is data, so it is written here in Home Assistant's configured language. The English below is
both the fallback and the source for `scripts/build_translations.py`, which publishes each
group under `entity.<PATH>.<key>` — the place Home Assistant keeps translated attribute values.

This module must stay free of Home Assistant imports: the build script loads it on its own.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Final

CALENDAR_SUMMARY: Final[dict[str, str]] = {
    "exercise": "Exercise",
    "last_exercise": "Last exercise",
    "maintenance_due": "Maintenance due",
}
CALENDAR_DESCRIPTION: Final[dict[str, str]] = {
    "last_exercise": "Most recent exercise run reported by the generator.",
    "scheduled": "Next scheduled exercise.",
    "projected": "Projected from the exercise schedule.",
    "maintenance_due": "Next scheduled maintenance for the generator.",
}
FIRMWARE_SUMMARY: Final[dict[str, str]] = {
    "released": "Released {date}.",
    "scheduled": "Scheduled to install {date}.",
    "auto_update_off": "Automatic firmware updates are off for this generator.",
}

# Where each group lives in the translation files, below `entity.`.
CALENDAR_SUMMARY_PATH: Final = "calendar.schedule.state_attributes.message.state"
CALENDAR_DESCRIPTION_PATH: Final = "calendar.schedule.state_attributes.description.state"
FIRMWARE_SUMMARY_PATH: Final = "update.firmware.state_attributes.release_summary.state"
EXERCISE_MODE_PATH: Final = "select.exercise_mode.state"

Texts = Mapping[str, str]


def text(texts: Texts | None, path: str, defaults: Mapping[str, str], key: str) -> str:
    """The translated text for `key`, or its English default."""
    return (texts or {}).get(f"{path}.{key}") or defaults[key]
