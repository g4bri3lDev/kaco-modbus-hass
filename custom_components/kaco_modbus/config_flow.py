"""Adding an inverter by address."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

import probatio
from homeassistant.components.modbus import async_get_temporary_unit
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    TextSelector,
)
from modbus_connection import ModbusError, ModbusTcpParams

from kaco_modbus import KacoError, KacoInverter, NotAKacoInverterError

from .const import CONF_UNIT_ID, DEFAULT_PORT, DEFAULT_UNIT_ID, DOMAIN

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from kaco_modbus import DeviceInfo

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = probatio.Schema(
    {
        probatio.Required(CONF_HOST): TextSelector(),
        probatio.Required(CONF_PORT, default=DEFAULT_PORT): probatio.All(
            NumberSelector(NumberSelectorConfig(mode=NumberSelectorMode.BOX, min=1, max=65535)),
            probatio.Coerce(int),
        ),
        probatio.Required(CONF_UNIT_ID, default=DEFAULT_UNIT_ID): probatio.All(
            NumberSelector(NumberSelectorConfig(mode=NumberSelectorMode.BOX, min=1, max=247)),
            probatio.Coerce(int),
        ),
    }
)


async def _async_probe(hass: HomeAssistant, host: str, port: int, unit_id: int) -> DeviceInfo:
    """Read the inverter's identity, or raise trying.

    There is no config entry yet to hold a unit against, so the modbus
    integration lends one for the length of the probe. If another entry
    already holds a connection to this device it is reused and left open,
    which matters here: a KACO accepts only one client at a time.
    """
    async with async_get_temporary_unit(
        hass, ModbusTcpParams(host=host, port=port), unit_id
    ) as unit:
        device = KacoInverter(unit)
        await device.async_update_readings()
        assert device.info is not None
        return device.info


class KacoConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for KACO."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Ask for an address and check a KACO inverter answers there."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                info = await _async_probe(
                    self.hass,
                    user_input[CONF_HOST],
                    user_input[CONF_PORT],
                    user_input[CONF_UNIT_ID],
                )
            except NotAKacoInverterError:
                errors["base"] = "not_a_kaco_inverter"
            except KacoError:
                errors["base"] = "not_a_sunspec_inverter"
            except HomeAssistantError:
                # The device is already held over different link settings,
                # which cannot both be honoured on one connection.
                errors["base"] = "already_in_use"
            except ModbusError:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                # The serial number is stable across address changes, which a
                # host or port is not.
                await self.async_set_unique_id(info.serial_number)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title=info.model, data=user_input)

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )
