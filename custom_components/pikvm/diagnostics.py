"""Diagnostics support for PiKVM."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant

from . import PiKVMConfigEntry
from .const import CONF_SSH_USERNAME

TO_REDACT = {CONF_PASSWORD, CONF_USERNAME, CONF_SSH_USERNAME}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    config_entry: PiKVMConfigEntry,
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    del hass
    runtime = config_entry.runtime_data
    coordinator = runtime.coordinator

    return {
        "entry": {
            "title": config_entry.title,
            "data": async_redact_data(dict(config_entry.data), TO_REDACT),
            "options": dict(config_entry.options),
        },
        "data": asdict(coordinator.data) if coordinator.data else None,
        "ocr": runtime.ocr_coordinator.data if runtime.ocr_coordinator else None,
    }
