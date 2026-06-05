"""Sensors for PiKVM."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import EntityCategory, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import PiKVMConfigEntry
from .const import ATTR_FULL_TEXT, OCR_STATE_MAX_LENGTH
from .coordinator import PiKVMOcrCoordinator
from .entity import PiKVMEntity, _dig, build_device_info


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: PiKVMConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the PiKVM sensors."""
    del hass
    runtime = config_entry.runtime_data

    entities: list[SensorEntity] = [
        PiKVMCpuTemperatureSensor(runtime.coordinator),
        PiKVMVersionSensor(runtime.coordinator),
    ]
    if runtime.ocr_coordinator is not None:
        entities.append(PiKVMOcrSensor(runtime.ocr_coordinator))

    async_add_entities(entities)


class PiKVMOcrSensor(CoordinatorEntity[PiKVMOcrCoordinator], SensorEntity):
    """OCR of the current screen content."""

    _attr_has_entity_name = True
    _attr_name = "OCR"
    _attr_icon = "mdi:ocr"

    def __init__(self, coordinator: PiKVMOcrCoordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_ocr"

    @property
    def device_info(self) -> DeviceInfo:
        """Return device information."""
        return build_device_info(self.coordinator.main_coordinator)

    @property
    def native_value(self) -> str | None:
        """Return the (truncated) OCR text."""
        text = self.coordinator.data
        if text is None:
            return None
        if len(text) > OCR_STATE_MAX_LENGTH:
            return f"{text[: OCR_STATE_MAX_LENGTH - 1]}…"
        return text

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Expose the full OCR text."""
        if self.coordinator.data is None:
            return None
        return {ATTR_FULL_TEXT: self.coordinator.data}


class PiKVMCpuTemperatureSensor(PiKVMEntity, SensorEntity):
    """CPU temperature of the PiKVM host."""

    _attr_name = "CPU temperature"
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, "cpu_temperature")

    @property
    def native_value(self) -> float | None:
        """Return the CPU temperature."""
        return _dig(self.coordinator.data.info, "hw", "health", "temp", "cpu")


class PiKVMVersionSensor(PiKVMEntity, SensorEntity):
    """Running kvmd version."""

    _attr_name = "kvmd version"
    _attr_icon = "mdi:tag"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, "kvmd_version")

    @property
    def native_value(self) -> str | None:
        """Return the kvmd version."""
        version = _dig(self.coordinator.data.info, "system", "kvmd", "version")
        return str(version) if version is not None else None
