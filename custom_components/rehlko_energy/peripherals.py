"""Shared plumbing for load-module (`loadShed`) and PIM (`pim`) parameter entities.

Both peripherals report `{isConnected, parameters: [{definitionId, displayName, value,
isReadOnly}]}`. A writable parameter is set with
`POST /devices/{id}/peripherals/{definitionId}/set_value {"value": ...}` and renamed with
`PUT /devices/{id}/peripherals/{definitionId} {"displayName": ...}`.
"""

from __future__ import annotations

from typing import Any

from .models import GeneratorData


def find_param(gen: GeneratorData | None, kind: str, definition_id: Any) -> dict[str, Any] | None:
    """The `kind` peripheral's parameter with this definition ID, if the generator reports it."""
    if gen is None:
        return None
    for param_kind, param in gen.peripheral_parameters():
        if param_kind == kind and str(param.get("definitionId")) == str(definition_id):
            return param
    return None


def writable_params(
    gen: GeneratorData, types: tuple[type, ...]
) -> list[tuple[str, dict[str, Any]]]:
    out = []
    for kind, param in gen.peripheral_parameters():
        value = param.get("value")
        if param.get("isReadOnly"):
            continue
        if bool in types:
            if isinstance(value, bool):
                out.append((kind, param))
        elif isinstance(value, types) and not isinstance(value, bool):
            out.append((kind, param))
    return out


class PeripheralMixin:
    """For entities bound to one peripheral parameter (mixed into a RehlkoEntity)."""

    _kind: str
    _definition_id: Any

    def _setup_peripheral(self, kind: str, definition_id: Any) -> None:
        self._kind = kind
        self._definition_id = definition_id
        self._attr_translation_key = "load_module_setting" if kind == "loadShed" else "pim_setting"
        param = self._param() or {}
        self._attr_translation_placeholders = {
            "name": str(param.get("displayName") or f"#{definition_id}")
        }

    def _param(self) -> dict[str, Any] | None:
        return find_param(self.gen, self._kind, self._definition_id)  # type: ignore[attr-defined]

    @property
    def available(self) -> bool:
        param = self._param()
        gen = self.gen  # type: ignore[attr-defined]
        return (
            super().available  # type: ignore[misc]
            and param is not None
            and not param.get("isReadOnly")
            and bool(gen and gen.is_connected)
        )

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        param = self._param() or {}
        return {
            "definition_id": self._definition_id,
            "display_name": param.get("displayName"),
            "peripheral": self._kind,
        }

    async def _write(self, value: Any) -> None:
        await self.coordinator.async_set_peripheral_value(  # type: ignore[attr-defined]
            self._device_id,
            self._definition_id,
            value,  # type: ignore[attr-defined]
        )
