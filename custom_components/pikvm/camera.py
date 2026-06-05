"""Camera for the PiKVM streamer snapshot."""

from __future__ import annotations

import logging

from homeassistant.components.camera import Camera
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import PiKVMConfigEntry
from .api import PiKVMApiError
from .entity import PiKVMEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: PiKVMConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the PiKVM camera."""
    del hass
    async_add_entities([PiKVMScreenCamera(config_entry.runtime_data.coordinator)])


class PiKVMScreenCamera(PiKVMEntity, Camera):
    """Snapshot camera showing the captured screen."""

    _attr_name = "Screen"
    _attr_brand = "PiKVM"

    def __init__(self, coordinator) -> None:
        """Initialize the camera."""
        PiKVMEntity.__init__(self, coordinator, "screen")
        Camera.__init__(self)

    async def async_camera_image(
        self,
        width: int | None = None,
        height: int | None = None,
    ) -> bytes | None:
        """Return the current streamer snapshot."""
        del width, height
        try:
            return await self.coordinator.client.async_get_snapshot()
        except PiKVMApiError as err:
            _LOGGER.debug("Snapshot failed: %s", err)
            return None
