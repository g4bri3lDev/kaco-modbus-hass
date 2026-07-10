"""The KACO blueplanet integration, over a shared Modbus connection."""

from __future__ import annotations

from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from kaco_modbus import KacoError, KacoInverter
from modbus_connection import ModbusError

from .const import CONF_CONNECTION_ENTRY_ID, CONF_UNIT_ID
from .coordinator import KacoConfigEntry, KacoCoordinator
from .provider import async_get_unit

PLATFORMS = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: KacoConfigEntry) -> bool:
    """Set up a KACO inverter from a config entry."""
    unit = async_get_unit(
        hass,
        str(entry.data[CONF_CONNECTION_ENTRY_ID]),
        int(entry.data[CONF_UNIT_ID]),
    )

    try:
        probe = await KacoInverter.async_probe(unit)
        device = KacoInverter(unit, probe)
    except (ModbusError, KacoError) as err:
        raise ConfigEntryNotReady(str(err)) from err

    coordinator = KacoCoordinator(hass, entry, device)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    entry.async_on_unload(
        unit.on_connection_lost(
            lambda: hass.config_entries.async_schedule_reload(entry.entry_id)
        )
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: KacoConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
