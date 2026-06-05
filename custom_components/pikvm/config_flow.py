"""Config flow for PiKVM."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import (
    CONF_HOST,
    CONF_NAME,
    CONF_PASSWORD,
    CONF_SCAN_INTERVAL,
    CONF_USERNAME,
    CONF_VERIFY_SSL,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_create_clientsession
from homeassistant.helpers.selector import (
    BooleanSelector,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .api import PiKVMApiClient, PiKVMApiError, PiKVMAuthError
from .const import (
    CONF_KEYMAP,
    CONF_OCR_ENABLED,
    CONF_OCR_LANG,
    CONF_OCR_SCAN_INTERVAL,
    CONF_SSH_ENABLED,
    CONF_SSH_KEY_PATH,
    CONF_SSH_PORT,
    CONF_SSH_USERNAME,
    DEFAULT_KEYMAP,
    DEFAULT_OCR_ENABLED,
    DEFAULT_OCR_LANG,
    DEFAULT_OCR_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_SSH_ENABLED,
    DEFAULT_SSH_KEY_PATH,
    DEFAULT_SSH_PORT,
    DEFAULT_SSH_USERNAME,
    DEFAULT_VERIFY_SSL,
    DOMAIN,
    MIN_SCAN_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)


async def _async_validate(hass: HomeAssistant, data: dict[str, Any]) -> None:
    """Validate that the kvmd API is reachable with the given credentials."""
    session = async_create_clientsession(
        hass,
        verify_ssl=data.get(CONF_VERIFY_SSL, DEFAULT_VERIFY_SSL),
    )
    client = PiKVMApiClient(
        session=session,
        host=data[CONF_HOST],
        username=data[CONF_USERNAME],
        password=data[CONF_PASSWORD],
    )
    await client.async_get_info()


def _user_schema(defaults: Mapping[str, Any]) -> vol.Schema:
    """Build the user step schema."""
    return vol.Schema(
        {
            vol.Required(CONF_HOST, default=defaults.get(CONF_HOST, "")): TextSelector(),
            vol.Optional(CONF_NAME, default=defaults.get(CONF_NAME, "PiKVM")): TextSelector(),
            vol.Required(
                CONF_USERNAME, default=defaults.get(CONF_USERNAME, "admin")
            ): TextSelector(),
            vol.Required(CONF_PASSWORD): TextSelector(
                TextSelectorConfig(type=TextSelectorType.PASSWORD)
            ),
            vol.Required(
                CONF_VERIFY_SSL,
                default=defaults.get(CONF_VERIFY_SSL, DEFAULT_VERIFY_SSL),
            ): BooleanSelector(),
            vol.Required(
                CONF_SSH_ENABLED,
                default=defaults.get(CONF_SSH_ENABLED, DEFAULT_SSH_ENABLED),
            ): BooleanSelector(),
            vol.Required(
                CONF_SSH_USERNAME,
                default=defaults.get(CONF_SSH_USERNAME, DEFAULT_SSH_USERNAME),
            ): TextSelector(),
            vol.Required(
                CONF_SSH_PORT,
                default=defaults.get(CONF_SSH_PORT, DEFAULT_SSH_PORT),
            ): NumberSelector(
                NumberSelectorConfig(min=1, max=65535, mode=NumberSelectorMode.BOX)
            ),
            vol.Required(
                CONF_SSH_KEY_PATH,
                default=defaults.get(CONF_SSH_KEY_PATH, DEFAULT_SSH_KEY_PATH),
            ): TextSelector(),
        }
    )


class PiKVMConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for PiKVM."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> PiKVMOptionsFlow:
        """Return the options flow for this handler."""
        del config_entry
        return PiKVMOptionsFlow()

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Handle the user step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                await _async_validate(self.hass, user_input)
            except PiKVMAuthError:
                errors["base"] = "invalid_auth"
            except PiKVMApiError:
                errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Unexpected exception while validating PiKVM config")
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(user_input[CONF_HOST])
                self._abort_if_unique_id_configured()
                title = user_input.pop(CONF_NAME, None) or "PiKVM"
                user_input[CONF_SSH_PORT] = int(user_input[CONF_SSH_PORT])
                return self.async_create_entry(title=title, data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=_user_schema(user_input or {}),
            errors=errors,
        )

    async def async_step_reauth(
        self,
        entry_data: Mapping[str, Any],
    ) -> ConfigFlowResult:
        """Handle reauthentication."""
        del entry_data
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Ask for new credentials."""
        errors: dict[str, str] = {}
        reauth_entry = self._get_reauth_entry()

        if user_input is not None:
            data = {**reauth_entry.data, **user_input}
            try:
                await _async_validate(self.hass, data)
            except PiKVMAuthError:
                errors["base"] = "invalid_auth"
            except PiKVMApiError:
                errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001
                _LOGGER.exception("Unexpected exception while validating PiKVM config")
                errors["base"] = "unknown"
            else:
                return self.async_update_reload_and_abort(reauth_entry, data=data)

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_USERNAME,
                        default=reauth_entry.data.get(CONF_USERNAME, "admin"),
                    ): TextSelector(),
                    vol.Required(CONF_PASSWORD): TextSelector(
                        TextSelectorConfig(type=TextSelectorType.PASSWORD)
                    ),
                }
            ),
            errors=errors,
        )


class PiKVMOptionsFlow(OptionsFlow):
    """Handle options for PiKVM."""

    async def async_step_init(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> ConfigFlowResult:
        """Manage the PiKVM options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        options = self.config_entry.options
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_SCAN_INTERVAL,
                        default=options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
                    ): NumberSelector(
                        NumberSelectorConfig(
                            min=MIN_SCAN_INTERVAL, mode=NumberSelectorMode.BOX, step=1
                        )
                    ),
                    vol.Required(
                        CONF_OCR_ENABLED,
                        default=options.get(CONF_OCR_ENABLED, DEFAULT_OCR_ENABLED),
                    ): BooleanSelector(),
                    vol.Required(
                        CONF_OCR_SCAN_INTERVAL,
                        default=options.get(
                            CONF_OCR_SCAN_INTERVAL, DEFAULT_OCR_SCAN_INTERVAL
                        ),
                    ): NumberSelector(
                        NumberSelectorConfig(
                            min=MIN_SCAN_INTERVAL, mode=NumberSelectorMode.BOX, step=1
                        )
                    ),
                    vol.Required(
                        CONF_OCR_LANG,
                        default=options.get(CONF_OCR_LANG, DEFAULT_OCR_LANG),
                    ): TextSelector(),
                    vol.Required(
                        CONF_KEYMAP,
                        default=options.get(CONF_KEYMAP, DEFAULT_KEYMAP),
                    ): TextSelector(),
                }
            ),
        )
