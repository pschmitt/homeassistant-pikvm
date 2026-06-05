"""Services for the PiKVM integration."""

from __future__ import annotations

import logging

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import config_validation as cv, device_registry as dr

from .api import PiKVMApiError
from .const import (
    ATTR_DELAY,
    ATTR_DEVICE_ID,
    ATTR_KEY,
    ATTR_KEYMAP,
    ATTR_SLOW,
    ATTR_TEXT,
    CONF_KEYMAP,
    DEFAULT_KEYMAP,
    DOMAIN,
    SERVICE_SEND_KEY,
    SERVICE_SEND_TEXT,
)

_LOGGER = logging.getLogger(__name__)

SEND_TEXT_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_TEXT): cv.string,
        vol.Optional(ATTR_SLOW, default=False): cv.boolean,
        vol.Optional(ATTR_DELAY): vol.Coerce(float),
        vol.Optional(ATTR_KEYMAP): cv.string,
        vol.Optional(ATTR_DEVICE_ID): cv.string,
    }
)

SEND_KEY_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_KEY): cv.string,
        vol.Optional(ATTR_DELAY): vol.Coerce(float),
        vol.Optional(ATTR_DEVICE_ID): cv.string,
    }
)


def _expand_text(text: str) -> str:
    """Expand newline placeholders, mirroring the legacy pikvm.sh behavior."""
    return text.replace("\\n", "\n").replace("<enter>", "\n")


def _async_resolve_entry(hass: HomeAssistant, call: ServiceCall) -> ConfigEntry:
    """Resolve the targeted config entry from the service call."""
    entries = [
        entry
        for entry in hass.config_entries.async_entries(DOMAIN)
        if entry.state is ConfigEntryState.LOADED
    ]
    if not entries:
        raise ServiceValidationError("No loaded PiKVM config entry found")

    device_id: str | None = call.data.get(ATTR_DEVICE_ID)
    if device_id is None:
        if len(entries) > 1:
            raise ServiceValidationError(
                "Multiple PiKVM devices are configured, please pass device_id"
            )
        return entries[0]

    device_registry = dr.async_get(hass)
    device = device_registry.async_get(device_id)
    if device is None:
        raise ServiceValidationError(f"Unknown device_id: {device_id}")
    for entry in entries:
        if entry.entry_id in device.config_entries:
            return entry
    raise ServiceValidationError(f"Device {device_id} is not a PiKVM device")


@callback
def async_setup_services(hass: HomeAssistant) -> None:
    """Register the PiKVM services."""

    async def async_handle_send_text(call: ServiceCall) -> None:
        """Type text on the PiKVM target."""
        entry = _async_resolve_entry(hass, call)
        client = entry.runtime_data.client
        keymap: str = call.data.get(ATTR_KEYMAP) or entry.options.get(
            CONF_KEYMAP, DEFAULT_KEYMAP
        )
        text = _expand_text(call.data[ATTR_TEXT])

        try:
            if call.data[ATTR_SLOW]:
                delay: float = call.data.get(ATTR_DELAY, 1.0)
                await client.async_send_text_slow(text, keymap, delay=delay)
            else:
                await client.async_send_text(text, keymap)
        except PiKVMApiError as err:
            raise HomeAssistantError(str(err)) from err

    async def async_handle_send_key(call: ServiceCall) -> None:
        """Press a single key on the PiKVM target."""
        entry = _async_resolve_entry(hass, call)
        client = entry.runtime_data.client

        try:
            await client.async_send_key(
                call.data[ATTR_KEY],
                delay=call.data.get(ATTR_DELAY, 0.2),
            )
        except PiKVMApiError as err:
            raise HomeAssistantError(str(err)) from err

    hass.services.async_register(
        DOMAIN, SERVICE_SEND_TEXT, async_handle_send_text, schema=SEND_TEXT_SCHEMA
    )
    hass.services.async_register(
        DOMAIN, SERVICE_SEND_KEY, async_handle_send_key, schema=SEND_KEY_SCHEMA
    )
