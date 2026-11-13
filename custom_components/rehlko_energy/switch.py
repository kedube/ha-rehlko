"""Switches: account notification preferences, automatic firmware updates, peripheral flags."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from . import RehlkoConfigEntry
from .api.util import humanize
from .coordinator import RehlkoCoordinator
from .entity import RehlkoAccountEntity, RehlkoEntity
from .peripherals import PeripheralMixin, writable_params

PARALLEL_UPDATES = 1

# `/homeowner/settings/notification` flags, in the app's order, with translation keys.
NOTIFICATION_SETTINGS: dict[str, str] = {
    "sendShutdowns": "notify_shutdowns",
    "sendWarnings": "notify_warnings",
    "sendGeneratorRunningNotices": "notify_running",
    "sendNotices": "notify_notices",
    "sendConnectionNotices": "notify_connection",
    "sendMaintenanceNotices": "notify_maintenance",
    "sendLongRunningNotices": "notify_long_running",
    "sendNotificationEmails": "notify_emails",
    "sendPushNotifications": "notify_push",
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: RehlkoConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    created: set[str] = set()

    @callback
    def _discover() -> None:
        new: list[SwitchEntity] = []
        settings = coordinator.data.notification_settings or {}
        for key, value in settings.items():
            if not isinstance(value, bool) or f"notify-{key}" in created:
                continue
            created.add(f"notify-{key}")
            new.append(NotificationSettingSwitch(coordinator, key))
        for device_id, gen in coordinator.data.generators.items():
            uid = f"{device_id}-auto_firmware_update"
            if uid not in created and isinstance(
                gen.details.get("autoFirmwareUpdateEnabled"), bool
            ):
                created.add(uid)
                new.append(AutoFirmwareUpdateSwitch(coordinator, device_id))
            for kind, param in writable_params(gen, (bool,)):
                uid = f"{device_id}-peripheral-switch-{param['definitionId']}"
                if uid not in created:
                    created.add(uid)
                    new.append(
                        PeripheralSwitch(coordinator, device_id, kind, param["definitionId"])
                    )
        if new:
            async_add_entities(new)

    _discover()
    entry.async_on_unload(coordinator.async_add_listener(_discover))


class NotificationSettingSwitch(RehlkoAccountEntity, SwitchEntity):
    """One of the account's notification categories (push and email from the app)."""

    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: RehlkoCoordinator, key: str) -> None:
        super().__init__(coordinator, f"notify-{key}")
        self._key = key
        if key in NOTIFICATION_SETTINGS:
            self._attr_translation_key = NOTIFICATION_SETTINGS[key]
        else:
            self._attr_translation_key = "notify_other"
            self._attr_translation_placeholders = {
                "name": humanize(key.removeprefix("send")) or key
            }

    @property
    def is_on(self) -> bool | None:
        settings = self.coordinator.data.notification_settings or {}
        value = settings.get(self._key)
        return value if isinstance(value, bool) else None

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.coordinator.async_set_notification_setting(self._key, True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.async_set_notification_setting(self._key, False)


class AutoFirmwareUpdateSwitch(RehlkoEntity, SwitchEntity):
    _attr_translation_key = "auto_firmware_update"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: RehlkoCoordinator, device_id: int) -> None:
        super().__init__(coordinator, device_id, "auto_firmware_update")

    @property
    def is_on(self) -> bool | None:
        gen = self.gen
        value = gen.details.get("autoFirmwareUpdateEnabled") if gen else None
        return value if isinstance(value, bool) else None

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.coordinator.async_update_device(self._device_id, autoFirmwareUpdateEnabled=True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.async_update_device(self._device_id, autoFirmwareUpdateEnabled=False)


class PeripheralSwitch(PeripheralMixin, RehlkoEntity, SwitchEntity):
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(
        self, coordinator: RehlkoCoordinator, device_id: int, kind: str, definition_id: Any
    ) -> None:
        super().__init__(coordinator, device_id, f"peripheral-switch-{definition_id}")
        self._setup_peripheral(kind, definition_id)

    @property
    def is_on(self) -> bool | None:
        value = (self._param() or {}).get("value")
        return value if isinstance(value, bool) else None

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._write(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._write(False)
