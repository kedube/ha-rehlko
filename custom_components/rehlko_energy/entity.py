"""Base entities and device metadata."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import TYPE_CHECKING, Any

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import translation
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER
from .coordinator import RehlkoCoordinator
from .models import GeneratorData

if TYPE_CHECKING:
    from . import RehlkoConfigEntry

APP_URL = "https://apps.apple.com/us/app/kohler-energy-management/id1627740645"
# How a device names its parent. Newer Home Assistant wants the parent's ID in the device
# registry (`via_device_id`) and deprecates the parent's identifier (`via_device`), which is all
# that older versions accept.
VIA_BY_REGISTRY_ID = "via_device_id" in DeviceInfo.__annotations__


async def async_entity_texts(hass: HomeAssistant) -> dict[str, str]:
    """This integration's entity translations in Home Assistant's language (see texts.py)."""
    prefix = f"component.{DOMAIN}.entity."
    strings = await translation.async_get_translations(
        hass, hass.config.language, "entity", {DOMAIN}
    )
    return {key.removeprefix(prefix): value for key, value in strings.items()}


@callback
def async_discover_generators(
    entry: RehlkoConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
    factory: Callable[[GeneratorData], Iterable[Entity]],
    eligible: Callable[[GeneratorData], bool] = lambda gen: True,
) -> None:
    """Add fixed entity sets when a generator first reports the required data."""
    coordinator = entry.runtime_data
    created: set[int] = set()

    @callback
    def _discover() -> None:
        entities: list[Entity] = []
        for gen in coordinator.data.generators.values():
            if gen.device_id in created or not gen.details_available or not eligible(gen):
                continue
            entities.extend(factory(gen))
            created.add(gen.device_id)
        if entities:
            async_add_entities(entities)

    _discover()
    entry.async_on_unload(coordinator.async_add_listener(_discover))


def generator_unique_id(entry_id: str, device_id: int, key: str) -> str:
    """Unique per account: one generator can be shared with two configured accounts."""
    return f"{entry_id}-{device_id}-{key}"


def generator_device_info(gen: GeneratorData) -> DeviceInfo:
    device = gen.device
    return DeviceInfo(
        identifiers={(DOMAIN, str(gen.device_id))},
        name=gen.name,
        manufacturer=MANUFACTURER,
        model=gen.model,
        model_id=device.get("model"),
        serial_number=gen.serial_number,
        sw_version=device.get("currentFirmware") or device.get("firmwareVersion"),
        hw_version=device.get("controllerType") or device.get("productDisplayName"),
        configuration_url=APP_URL,
    )


def ats_device_info(
    gen: GeneratorData, coordinator: RehlkoCoordinator | None = None
) -> DeviceInfo | None:
    """The transfer switch's device, or None if the generator reports no switch.

    With a coordinator, the switch is linked to its generator's device, which is registered
    first if no entity of the generator has done so yet.
    """
    ats = gen.ats
    serial = ats.get("serialNumber")
    if not ats or not serial:
        return None
    info = DeviceInfo(
        identifiers={(DOMAIN, f"{gen.device_id}:ats")},
        name=ats.get("displayName") or f"{gen.name} transfer switch",
        manufacturer=MANUFACTURER,
        model=ats.get("modelNo") or "Automatic transfer switch",
        serial_number=serial,
    )
    if coordinator is not None:
        parent = dr.async_get(coordinator.hass).async_get_or_create(
            config_entry_id=coordinator.config_entry.entry_id, **generator_device_info(gen)
        )
        if VIA_BY_REGISTRY_ID:
            info["via_device_id"] = parent.id
        else:
            info["via_device"] = (DOMAIN, str(gen.device_id))
    return info


def account_device_info(coordinator: RehlkoCoordinator) -> DeviceInfo:
    entry = coordinator.config_entry
    return DeviceInfo(
        identifiers={(DOMAIN, f"account:{entry.entry_id}")},
        name=f"Rehlko account ({entry.title})",
        manufacturer=MANUFACTURER,
        model="Energy Management account",
        entry_type=DeviceEntryType.SERVICE,
        configuration_url=APP_URL,
    )


class RehlkoEntity(CoordinatorEntity[RehlkoCoordinator]):
    """An entity of one generator."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: RehlkoCoordinator,
        device_id: int,
        key: str,
        *,
        device_info: DeviceInfo | None = None,
    ) -> None:
        super().__init__(coordinator)
        self._device_id = device_id
        self._attr_unique_id = generator_unique_id(
            coordinator.config_entry.entry_id, device_id, key
        )
        gen = coordinator.data.generators[device_id]
        self._attr_device_info = device_info or generator_device_info(gen)

    @property
    def gen(self) -> GeneratorData | None:
        data = self.coordinator.data
        return data.generators.get(self._device_id) if data else None

    @property
    def available(self) -> bool:
        return super().available and self.gen is not None and self.gen.details_available


class RehlkoAccountEntity(CoordinatorEntity[RehlkoCoordinator]):
    """An entity of the account itself (notification preferences)."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: RehlkoCoordinator, key: str) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"account-{coordinator.config_entry.entry_id}-{key}"
        self._attr_device_info = account_device_info(coordinator)


def value_or_none(fn: Callable[[GeneratorData], Any], gen: GeneratorData | None) -> Any:
    if gen is None:
        return None
    try:
        return fn(gen)
    except (KeyError, TypeError, ValueError, AttributeError, IndexError):
        return None
