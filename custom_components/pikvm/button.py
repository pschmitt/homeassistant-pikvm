"""Buttons for PiKVM."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import PiKVMConfigEntry
from .api import PiKVMApiError
from .entity import PiKVMEntity
from .ssh import PiKVMSshError


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: PiKVMConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the PiKVM buttons."""
    del hass
    runtime = config_entry.runtime_data
    coordinator = runtime.coordinator

    entities: list[ButtonEntity] = [PiKVMResetButton(coordinator)]

    if runtime.ssh_client is not None:
        entities.append(PiKVMShutdownButton(coordinator, runtime.ssh_client))

    if coordinator.data and coordinator.data.atx.get("enabled"):
        entities.extend(
            PiKVMAtxButton(coordinator, action, name)
            for action, name in (
                ("on", "ATX power on"),
                ("off", "ATX power off"),
                ("reset_hard", "ATX reset"),
            )
        )

    async_add_entities(entities)


class PiKVMResetButton(PiKVMEntity, ButtonEntity):
    """Reset the streamer and HID subsystems."""

    _attr_name = "Reset stream"
    _attr_icon = "mdi:restart"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator) -> None:
        """Initialize the button."""
        super().__init__(coordinator, "reset")

    async def async_press(self) -> None:
        """Reset the streamer and HID."""
        try:
            await self.coordinator.client.async_reset()
        except PiKVMApiError as err:
            raise HomeAssistantError(str(err)) from err


class PiKVMShutdownButton(PiKVMEntity, ButtonEntity):
    """Shut down the PiKVM host."""

    _attr_name = "Shutdown"
    _attr_icon = "mdi:power"

    def __init__(self, coordinator, ssh_client) -> None:
        """Initialize the button."""
        super().__init__(coordinator, "shutdown")
        self._ssh_client = ssh_client

    async def async_press(self) -> None:
        """Shut down the host."""
        try:
            await self._ssh_client.async_shutdown()
        except PiKVMSshError as err:
            raise HomeAssistantError(str(err)) from err


class PiKVMAtxButton(PiKVMEntity, ButtonEntity):
    """Send an ATX power action to the attached target host."""

    def __init__(self, coordinator, action: str, name: str) -> None:
        """Initialize the button."""
        super().__init__(coordinator, f"atx_{action}")
        self._action = action
        self._attr_name = name
        self._attr_icon = "mdi:power-settings"

    async def async_press(self) -> None:
        """Send the ATX action."""
        try:
            await self.coordinator.client.async_atx_power(self._action)
        except PiKVMApiError as err:
            raise HomeAssistantError(str(err)) from err
