"""Binary sensors for PiKVM."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import PiKVMConfigEntry
from .entity import PiKVMEntity, _dig


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: PiKVMConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the PiKVM binary sensors."""
    del hass
    runtime = config_entry.runtime_data
    coordinator = runtime.coordinator

    entities: list[BinarySensorEntity] = [PiKVMOnlineBinarySensor(coordinator)]

    if runtime.ssh_client is not None:
        entities.append(PiKVMUpdatingBinarySensor(coordinator))

    if coordinator.data and coordinator.data.atx.get("enabled"):
        entities.append(PiKVMAtxPowerBinarySensor(coordinator))

    async_add_entities(entities)


class PiKVMOnlineBinarySensor(PiKVMEntity, BinarySensorEntity):
    """Whether the kvmd API is reachable."""

    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_name = "Online"

    def __init__(self, coordinator) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator, "online")

    @property
    def available(self) -> bool:
        """The sensor itself is always available; offline is its off state."""
        return self.coordinator.last_update_success

    @property
    def is_on(self) -> bool:
        """Return True when the kvmd API is reachable."""
        return bool(self.coordinator.data and self.coordinator.data.online)


class PiKVMUpdatingBinarySensor(PiKVMEntity, BinarySensorEntity):
    """Whether a pacman update is currently in progress."""

    _attr_name = "Updating"
    _attr_icon = "mdi:package-down"

    def __init__(self, coordinator) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator, "updating")

    @property
    def available(self) -> bool:
        """Available only when the SSH status could be fetched."""
        return super().available and self.coordinator.data.ssh.updating is not None

    @property
    def is_on(self) -> bool | None:
        """Return True while the pacman database is locked."""
        return self.coordinator.data.ssh.updating


class PiKVMAtxPowerBinarySensor(PiKVMEntity, BinarySensorEntity):
    """Power state of the ATX-attached target host."""

    _attr_device_class = BinarySensorDeviceClass.POWER
    _attr_name = "Target power"

    def __init__(self, coordinator) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator, "atx_power")

    @property
    def is_on(self) -> bool | None:
        """Return the ATX power LED state."""
        return _dig(self.coordinator.data.atx, "leds", "power")
