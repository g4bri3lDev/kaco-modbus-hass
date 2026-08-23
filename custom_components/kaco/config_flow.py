"""Adding an inverter by address."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_HOST, CONF_PORT
from kaco_modbus import KacoError, KacoInverter
from modbus_connection import ModbusError, ModbusTcpParams
from modbus_connection.tmodbus import ModbusConnection

from .const import CONF_UNIT_ID, DEFAULT_PORT, DEFAULT_UNIT_ID, DOMAIN

if TYPE_CHECKING:
    from kaco_modbus import DeviceInfo

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_PORT, default=DEFAULT_PORT): int,
        vol.Required(CONF_UNIT_ID, default=DEFAULT_UNIT_ID): int,
    }
)


async def _async_probe(host: str, port: int, unit_id: int) -> DeviceInfo:
    """Read the inverter's identity, or raise trying.

    Opens a connection of its own and closes it again: the entry is not set up
    yet, and most Modbus devices refuse a second concurrent client.
    """
    connection = ModbusConnection(ModbusTcpParams(host=host, port=port))
    try:
        device = KacoInverter(connection.for_unit(unit_id))
        await device.async_update_readings()
        assert device.info is not None
        return device.info
    finally:
        await connection.close()


class KacoConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for KACO."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Ask for an address and check something answers there."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                info = await _async_probe(
                    user_input[CONF_HOST],
                    user_input[CONF_PORT],
                    user_input[CONF_UNIT_ID],
                )
            except KacoError:
                # Something answered Modbus, but it is not a SunSpec inverter.
                errors["base"] = "not_a_kaco_inverter"
            except ModbusError:
                errors["base"] = "cannot_connect"
            else:
                # The serial number is stable across address changes, which a
                # host or port is not.
                await self.async_set_unique_id(info.serial_number)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title=info.model, data=user_input)

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )
