"""The KACO integration.

The config entry owns the Modbus connection; the library only ever sees a
``ModbusUnit``. That is the shape Home Assistant's shared-connection work
expects, so adopting it later is a change to this file alone.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT, Platform
from homeassistant.exceptions import ConfigEntryNotReady
from kaco_modbus import KacoInverter
from modbus_connection import ModbusError, ModbusTcpParams
from modbus_connection.tmodbus import ModbusConnection

from .const import CONF_UNIT_ID, READINGS_INTERVAL, SETTINGS_INTERVAL
from .coordinator import KacoCoordinator

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

PLATFORMS: list[Platform] = [
    Platform.NUMBER,
    Platform.SELECT,
    Platform.SENSOR,
    Platform.SWITCH,
]


@dataclass
class KacoData:
    """What a loaded config entry holds."""

    device: KacoInverter
    readings: KacoCoordinator
    settings: KacoCoordinator


type KacoConfigEntry = ConfigEntry[KacoData]


async def async_setup_entry(hass: HomeAssistant, entry: KacoConfigEntry) -> bool:
    """Set up KACO from a config entry."""
    connection = ModbusConnection(
        ModbusTcpParams(host=entry.data[CONF_HOST], port=entry.data[CONF_PORT])
    )
    # Registered before anything can fail, so a half-finished setup still
    # closes the socket.
    entry.async_on_unload(connection.close)

    device = KacoInverter(connection.for_unit(entry.data[CONF_UNIT_ID]))

    readings = KacoCoordinator(
        hass,
        entry,
        connection,
        device,
        device.async_update_readings,
        READINGS_INTERVAL,
        "readings",
    )
    settings = KacoCoordinator(
        hass,
        entry,
        connection,
        device,
        device.async_update_settings,
        SETTINGS_INTERVAL,
        "settings",
    )

    # Deliberately no on_connection_lost reload: every request connects first,
    # so a dropped link heals on the next poll.
    try:
        await readings.async_config_entry_first_refresh()
        await settings.async_config_entry_first_refresh()
    except ModbusError as err:
        raise ConfigEntryNotReady(str(err)) from err

    entry.runtime_data = KacoData(device=device, readings=readings, settings=settings)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: KacoConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
