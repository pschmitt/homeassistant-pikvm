"""The PiKVM integration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME, CONF_VERIFY_SSL
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_create_clientsession

from .api import PiKVMApiClient
from .const import (
    CONF_OCR_ENABLED,
    CONF_SSH_ENABLED,
    CONF_SSH_KEY_PATH,
    CONF_SSH_PORT,
    CONF_SSH_USERNAME,
    DEFAULT_OCR_ENABLED,
    DEFAULT_SSH_ENABLED,
    DEFAULT_SSH_KEY_PATH,
    DEFAULT_SSH_PORT,
    DEFAULT_SSH_USERNAME,
    DEFAULT_VERIFY_SSL,
    DOMAIN,
    PLATFORMS,
)
from .coordinator import PiKVMDataUpdateCoordinator, PiKVMOcrCoordinator
from .services import async_setup_services
from .ssh import PiKVMSshClient


@dataclass
class PiKVMRuntimeData:
    """Runtime data for a PiKVM config entry."""

    client: PiKVMApiClient
    ssh_client: PiKVMSshClient | None
    coordinator: PiKVMDataUpdateCoordinator
    ocr_coordinator: PiKVMOcrCoordinator | None


type PiKVMConfigEntry = ConfigEntry[PiKVMRuntimeData]


async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    """Set up the PiKVM integration."""
    del config
    async_setup_services(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, config_entry: PiKVMConfigEntry) -> bool:
    """Set up PiKVM from a config entry."""
    session = async_create_clientsession(
        hass,
        verify_ssl=config_entry.data.get(CONF_VERIFY_SSL, DEFAULT_VERIFY_SSL),
    )
    client = PiKVMApiClient(
        session=session,
        host=config_entry.data[CONF_HOST],
        username=config_entry.data[CONF_USERNAME],
        password=config_entry.data[CONF_PASSWORD],
    )

    ssh_client: PiKVMSshClient | None = None
    if config_entry.data.get(CONF_SSH_ENABLED, DEFAULT_SSH_ENABLED):
        ssh_client = PiKVMSshClient(
            host=config_entry.data[CONF_HOST],
            username=config_entry.data.get(CONF_SSH_USERNAME, DEFAULT_SSH_USERNAME),
            port=config_entry.data.get(CONF_SSH_PORT, DEFAULT_SSH_PORT),
            key_path=config_entry.data.get(CONF_SSH_KEY_PATH, DEFAULT_SSH_KEY_PATH),
        )

    coordinator = PiKVMDataUpdateCoordinator(hass, config_entry, client, ssh_client)
    await coordinator.async_config_entry_first_refresh()

    ocr_coordinator: PiKVMOcrCoordinator | None = None
    if config_entry.options.get(CONF_OCR_ENABLED, DEFAULT_OCR_ENABLED):
        ocr_coordinator = PiKVMOcrCoordinator(hass, config_entry, client, coordinator)
        await ocr_coordinator.async_config_entry_first_refresh()

    config_entry.runtime_data = PiKVMRuntimeData(
        client=client,
        ssh_client=ssh_client,
        coordinator=coordinator,
        ocr_coordinator=ocr_coordinator,
    )

    await hass.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)
    config_entry.async_on_unload(config_entry.add_update_listener(async_update_listener))
    return True


async def async_unload_entry(hass: HomeAssistant, config_entry: PiKVMConfigEntry) -> bool:
    """Unload a PiKVM config entry."""
    return await hass.config_entries.async_unload_platforms(config_entry, PLATFORMS)


async def async_update_listener(hass: HomeAssistant, config_entry: PiKVMConfigEntry) -> None:
    """Reload the integration after options changes."""
    await hass.config_entries.async_reload(config_entry.entry_id)
