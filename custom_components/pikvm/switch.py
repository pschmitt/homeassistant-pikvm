"""Switches for PiKVM (SSH-backed LED and OLED controls)."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import PiKVMConfigEntry
from .coordinator import PiKVMDataUpdateCoordinator
from .entity import PiKVMEntity
from .ssh import PiKVMSshClient, PiKVMSshError


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: PiKVMConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the PiKVM switches."""
    del hass
    runtime = config_entry.runtime_data
    if runtime.ssh_client is None:
        return

    async_add_entities(
        [
            PiKVMLedsSwitch(runtime.coordinator, runtime.ssh_client),
            PiKVMOledSwitch(runtime.coordinator, runtime.ssh_client),
        ]
    )


class PiKVMSshSwitch(PiKVMEntity, SwitchEntity):
    """Base class for SSH-backed switches."""

    _attr_entity_category = EntityCategory.CONFIG
    _state_attribute: str

    def __init__(
        self,
        coordinator: PiKVMDataUpdateCoordinator,
        ssh_client: PiKVMSshClient,
        key: str,
    ) -> None:
        """Initialize the switch."""
        super().__init__(coordinator, key)
        self._ssh_client = ssh_client

    @property
    def available(self) -> bool:
        """Available only when the SSH status could be fetched."""
        return super().available and self.is_on is not None

    @property
    def is_on(self) -> bool | None:
        """Return the switch state from the coordinator."""
        return getattr(self.coordinator.data.ssh, self._state_attribute)

    async def _async_apply(self, enabled: bool) -> None:
        """Run the SSH command and refresh the state."""
        raise NotImplementedError

    async def _async_set(self, enabled: bool) -> None:
        try:
            await self._async_apply(enabled)
        except PiKVMSshError as err:
            raise HomeAssistantError(str(err)) from err
        setattr(self.coordinator.data.ssh, self._state_attribute, enabled)
        self.coordinator.async_set_updated_data(self.coordinator.data)
        await self.coordinator.async_request_refresh()

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        del kwargs
        await self._async_set(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        del kwargs
        await self._async_set(False)


class PiKVMLedsSwitch(PiKVMSshSwitch):
    """Raspberry Pi status LEDs."""

    _attr_name = "LEDs"
    _attr_icon = "mdi:led-on"
    _state_attribute = "leds_on"

    def __init__(self, coordinator, ssh_client) -> None:
        """Initialize the switch."""
        super().__init__(coordinator, ssh_client, "leds")

    async def _async_apply(self, enabled: bool) -> None:
        await self._ssh_client.async_set_leds(enabled)


class PiKVMOledSwitch(PiKVMSshSwitch):
    """kvmd OLED screen."""

    _attr_name = "OLED"
    _attr_icon = "mdi:overscan"
    _state_attribute = "oled_on"

    def __init__(self, coordinator, ssh_client) -> None:
        """Initialize the switch."""
        super().__init__(coordinator, ssh_client, "oled")

    async def _async_apply(self, enabled: bool) -> None:
        await self._ssh_client.async_set_oled(enabled)
