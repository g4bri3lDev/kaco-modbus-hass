"""Config flow for the KACO blueplanet integration."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
)
from kaco_modbus import KacoError, KacoInverter, KacoProbe
from modbus_connection import ModbusError

from .const import (
    CONF_CONNECTION_ENTRY_ID,
    CONF_UNIT_ID,
    DEFAULT_UNIT_ID,
    DOMAIN,
    MODBUS_CONNECTION_DOMAIN,
)
from .provider import async_get_unit

_UNIT = NumberSelector(
    NumberSelectorConfig(min=1, max=247, step=1, mode=NumberSelectorMode.BOX)
)


def _connection_options(hass: HomeAssistant) -> dict[str, str]:
    """Selectable Modbus Connection config entries."""
    entries = sorted(
        hass.config_entries.async_entries(MODBUS_CONNECTION_DOMAIN),
        key=lambda entry: entry.title.casefold(),
    )
    return {
        entry.entry_id: entry.title or entry.entry_id
        for entry in entries
        if entry.disabled_by is None
    }


class KacoConfigFlow(ConfigFlow, domain=DOMAIN):
    """Select a shared Modbus connection and probe the inverter."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        connections = _connection_options(self.hass)

        if not connections:
            return self.async_abort(reason="no_modbus_connection")

        if user_input is not None:
            data = {
                CONF_CONNECTION_ENTRY_ID: str(user_input[CONF_CONNECTION_ENTRY_ID]),
                CONF_UNIT_ID: int(user_input[CONF_UNIT_ID]),
            }
            probe = await self._async_probe(data)
            if probe is None:
                errors["base"] = "cannot_connect"
            else:
                await self.async_set_unique_id(probe.serial)
                self._abort_if_unique_id_configured()
                title = (
                    " ".join(part for part in (probe.manufacturer, probe.model) if part)
                    or "KACO inverter"
                )
                return self.async_create_entry(title=title, data=data)

        schema = vol.Schema(
            {
                vol.Required(CONF_CONNECTION_ENTRY_ID): vol.In(connections),
                vol.Required(CONF_UNIT_ID, default=DEFAULT_UNIT_ID): _UNIT,
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    async def _async_probe(self, data: dict[str, Any]) -> KacoProbe | None:
        try:
            unit = async_get_unit(
                self.hass, data[CONF_CONNECTION_ENTRY_ID], data[CONF_UNIT_ID]
            )
            return await KacoInverter.async_probe(unit)
        except (ConfigEntryNotReady, ModbusError, KacoError, OSError, ValueError):
            return None
