"""Base entities for PiKVM."""

from __future__ import annotations

from typing import Any

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import PiKVMDataUpdateCoordinator


def _dig(data: dict[str, Any], *keys: str) -> Any:
    """Safely walk a nested dict."""
    current: Any = data
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def build_device_info(coordinator: PiKVMDataUpdateCoordinator) -> DeviceInfo:
    """Return the device info for the PiKVM device."""
    info = coordinator.data.info if coordinator.data else {}
    platform = _dig(info, "hw", "platform") or {}

    return DeviceInfo(
        identifiers={(DOMAIN, coordinator.config_entry.entry_id)},
        name=coordinator.config_entry.title,
        manufacturer="PiKVM",
        model=platform.get("model"),
        hw_version=platform.get("base"),
        serial_number=platform.get("serial"),
        sw_version=_dig(info, "system", "kvmd", "version"),
        configuration_url=coordinator.client.base_url,
    )


class PiKVMEntity(CoordinatorEntity[PiKVMDataUpdateCoordinator]):
    """Base PiKVM entity."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: PiKVMDataUpdateCoordinator, key: str) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{key}"

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        return build_device_info(self.coordinator)

    @property
    def available(self) -> bool:
        """Consider the entity unavailable while the device is offline."""
        return (
            self.coordinator.last_update_success
            and self.coordinator.data is not None
            and self.coordinator.data.online
        )
