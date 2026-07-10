"""DataUpdateCoordinator polling the inverter through a shared Modbus unit."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)
from kaco_modbus import KacoInverter
from modbus_connection import ModbusError

from .const import DOMAIN, SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)

type KacoConfigEntry = ConfigEntry[KacoCoordinator]


class KacoCoordinator(DataUpdateCoordinator[KacoInverter]):
    """Poll a KACO inverter."""

    def __init__(
        self, hass: HomeAssistant, entry: KacoConfigEntry, device: KacoInverter
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            config_entry=entry,
            update_interval=SCAN_INTERVAL,
        )
        self.device = device
        self._first_refresh_succeeded = False
        self._reload_scheduled = False

    async def _async_update_data(self) -> KacoInverter:
        try:
            await self.device.async_update()
        except ModbusError as err:
            if self._first_refresh_succeeded and not self._reload_scheduled:
                self._reload_scheduled = True
                self.hass.config_entries.async_schedule_reload(
                    self.config_entry.entry_id
                )
            raise UpdateFailed(f"Error communicating with inverter: {err}") from err
        self._first_refresh_succeeded = True
        return self.device
