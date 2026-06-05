"""Lights for PiKVM (SSH-backed Raspberry Pi status LEDs)."""

from __future__ import annotations

from typing import Any

from homeassistant.components.light import ColorMode, LightEntity
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
    """Set up the PiKVM lights."""
    del hass
    runtime = config_entry.runtime_data
    if runtime.ssh_client is None:
        return

    async_add_entities([PiKVMLedsLight(runtime.coordinator, runtime.ssh_client)])


class PiKVMLedsLight(PiKVMEntity, LightEntity):
    """Raspberry Pi status LEDs."""

    _attr_name = "LEDs"
    _attr_icon = "mdi:led-on"
    _attr_color_mode = ColorMode.ONOFF
    _attr_supported_color_modes = {ColorMode.ONOFF}
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(
        self,
        coordinator: PiKVMDataUpdateCoordinator,
        ssh_client: PiKVMSshClient,
    ) -> None:
        """Initialize the light."""
        super().__init__(coordinator, "leds")
        self._ssh_client = ssh_client

    @property
    def available(self) -> bool:
        """Available only when the SSH status could be fetched."""
        return super().available and self.is_on is not None

    @property
    def is_on(self) -> bool | None:
        """Return whether the LEDs are enabled."""
        return self.coordinator.data.ssh.leds_on

    async def _async_set(self, enabled: bool) -> None:
        try:
            await self._ssh_client.async_set_leds(enabled)
        except PiKVMSshError as err:
            raise HomeAssistantError(str(err)) from err
        self.coordinator.data.ssh.leds_on = enabled
        self.coordinator.async_set_updated_data(self.coordinator.data)
        await self.coordinator.async_request_refresh()

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the LEDs on."""
        del kwargs
        await self._async_set(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the LEDs off."""
        del kwargs
        await self._async_set(False)
