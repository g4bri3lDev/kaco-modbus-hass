"""The KACO Modbus integration.

Home Assistant's ``modbus`` integration owns the connection and hands out a
``ModbusUnit`` on it. Consumers of one device therefore share a single link,
which matters here: a KACO accepts only one Modbus client at a time.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from homeassistant.components.modbus import async_get_unit
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT, Platform
from homeassistant.exceptions import ConfigEntryNotReady
from modbus_connection import ModbusError, ModbusTcpParams

from kaco_modbus import KacoInverter

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
    # The modbus integration owns the connection and closes it behind the last
    # entry holding a unit on it, registering that release on this entry — so
    # there is deliberately nothing to close here.
    unit = async_get_unit(
        hass,
        entry,
        ModbusTcpParams(host=entry.data[CONF_HOST], port=entry.data[CONF_PORT]),
        entry.data[CONF_UNIT_ID],
    )
    device = KacoInverter(unit)

    readings = KacoCoordinator(
        hass,
        entry,
        unit,
        device,
        device.async_update_readings,
        READINGS_INTERVAL,
        "readings",
    )
    settings = KacoCoordinator(
        hass,
        entry,
        unit,
        device,
        device.async_update_settings,
        SETTINGS_INTERVAL,
        "settings",
    )

    # Deliberately no reload on a dropped connection: every request connects
    # first, so a broken link heals on the next poll.
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
