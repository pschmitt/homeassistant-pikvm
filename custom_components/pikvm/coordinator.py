"""Data update coordinators for PiKVM."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .api import PiKVMApiClient, PiKVMApiError, PiKVMAuthError
from .const import (
    CONF_OCR_LANG,
    CONF_OCR_SCAN_INTERVAL,
    DEFAULT_OCR_LANG,
    DEFAULT_OCR_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)
from .ssh import PiKVMSshClient, PiKVMSshError, PiKVMSshStatus

_LOGGER = logging.getLogger(__name__)


@dataclass
class PiKVMData:
    """State of one PiKVM device."""

    online: bool = False
    info: dict[str, Any] = field(default_factory=dict)
    atx: dict[str, Any] = field(default_factory=dict)
    ssh: PiKVMSshStatus = field(default_factory=PiKVMSshStatus)


class PiKVMDataUpdateCoordinator(DataUpdateCoordinator[PiKVMData]):
    """Poll the kvmd API (and optionally SSH) for device state.

    An unreachable PiKVM is a normal state (it is commonly powered off via
    PoE), so connection errors mark the device offline instead of failing
    the update.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        client: PiKVMApiClient,
        ssh_client: PiKVMSshClient | None,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{config_entry.entry_id}",
            update_interval=timedelta(
                seconds=config_entry.options.get(
                    CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
                )
            ),
        )
        self.config_entry = config_entry
        self.client = client
        self.ssh_client = ssh_client
        self._ssh_failure_logged = False

    async def _async_update_data(self) -> PiKVMData:
        """Fetch the current device state."""
        data = PiKVMData()

        try:
            data.info = await self.client.async_get_info()
        except PiKVMAuthError as err:
            raise ConfigEntryAuthFailed from err
        except PiKVMApiError as err:
            _LOGGER.debug("PiKVM %s is offline: %s", self.client.host, err)
            return data

        data.online = True

        try:
            data.atx = await self.client.async_get_atx()
        except PiKVMApiError as err:
            _LOGGER.debug("Failed to fetch ATX state: %s", err)

        if self.ssh_client is not None:
            try:
                data.ssh = await self.ssh_client.async_get_status()
            except PiKVMSshError as err:
                if not self._ssh_failure_logged:
                    _LOGGER.warning("SSH status fetch failed: %s", err)
                    self._ssh_failure_logged = True
            else:
                self._ssh_failure_logged = False

        return data


class PiKVMOcrCoordinator(DataUpdateCoordinator[str | None]):
    """Periodically OCR the captured screen."""

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        client: PiKVMApiClient,
        main_coordinator: PiKVMDataUpdateCoordinator,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{config_entry.entry_id}_ocr",
            update_interval=timedelta(
                seconds=config_entry.options.get(
                    CONF_OCR_SCAN_INTERVAL, DEFAULT_OCR_SCAN_INTERVAL
                )
            ),
        )
        self.config_entry = config_entry
        self.client = client
        self.main_coordinator = main_coordinator
        self.lang: str = config_entry.options.get(CONF_OCR_LANG, DEFAULT_OCR_LANG)

    async def _async_update_data(self) -> str | None:
        """Run OCR on the current screen content."""
        main_data = self.main_coordinator.data
        if main_data is None or not main_data.online:
            return None

        try:
            return await self.client.async_get_ocr(self.lang)
        except PiKVMApiError as err:
            _LOGGER.debug("OCR failed: %s", err)
            return None
