"""Polling, and what to do when an inverter stops answering."""

from __future__ import annotations

import logging
from functools import cached_property
from typing import TYPE_CHECKING

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from modbus_connection import ModbusError, ModbusTimeoutError

from kaco_modbus import MANUFACTURER, SunSpecMapShiftError

from .const import DOMAIN, TIMEOUTS_BEFORE_DISCONNECT

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable
    from datetime import timedelta

    from homeassistant.core import HomeAssistant
    from modbus_connection import ModbusUnit

    from kaco_modbus import KacoInverter, UpdateReport

    from . import KacoConfigEntry

_LOGGER = logging.getLogger(__name__)


class KacoCoordinator(DataUpdateCoordinator["UpdateReport"]):
    """Run one of the device's update methods on its own interval.

    Two of these share an inverter: readings poll often, settings rarely.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        entry: KacoConfigEntry,
        unit: ModbusUnit,
        device: KacoInverter,
        poll: Callable[[], Awaitable[UpdateReport]],
        interval: timedelta,
        name: str,
    ) -> None:
        """Set up a coordinator driving *poll* every *interval*."""
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=f"{entry.title} {name}",
            update_interval=interval,
        )
        self.entry = entry
        self.device = device
        self._unit = unit
        self._poll = poll
        self._failed: frozenset[str] = frozenset()
        self._timeouts = 0

    async def _async_note_timeout(self) -> None:
        """Count a silent poll, and recycle a link that has stopped answering.

        Safe on a shared connection: disconnect is a passthrough that leaves
        the connection owned by the modbus integration, which rebuilds it on
        the next request. Closing it is deliberately not possible from a unit,
        so one consumer cannot take it away from the others.
        """
        self._timeouts += 1
        if self._timeouts >= TIMEOUTS_BEFORE_DISCONNECT:
            _LOGGER.debug(
                "No answer from %s after %s attempts; recycling the link",
                self.entry.title,
                self._timeouts,
            )
            await self._unit.disconnect()
            self._timeouts = 0

    async def _async_update_data(self) -> UpdateReport:
        """Refresh one category, and report what actually came back."""
        try:
            report = await self._poll()
        except SunSpecMapShiftError as err:
            # The model chain moved, so every bound register offset is stale.
            # Nothing short of rediscovery fixes that. Note this is *not* a
            # ModbusError, so it needs its own clause.
            self.hass.config_entries.async_schedule_reload(self.entry.entry_id)
            raise UpdateFailed(f"the SunSpec map moved: {err}") from err
        except ModbusError as err:
            # The library only raises what it could not attribute to one
            # component; anything per-component arrives in the report instead.
            if isinstance(err, ModbusTimeoutError):
                await self._async_note_timeout()
            raise UpdateFailed(str(err)) from err

        if not report.updated:
            errors = list(report.failed.values())
            # Nothing answered. The library polls each component separately and
            # records a ModbusTimeoutError rather than raising it, so a silent
            # inverter shows up here rather than in the except clause above —
            # which is why the timeout count has to be kept from the report too.
            if errors and all(isinstance(err, ModbusTimeoutError) for err in errors):
                await self._async_note_timeout()
            raise UpdateFailed(f"nothing answered: {errors[0]}") from ExceptionGroup(
                "every sub-system failed", errors
            )

        self._timeouts = 0

        # A partial poll still publishes what worked. Log only sub-systems that
        # have newly started failing, so a long outage does not fill the log.
        for name in sorted(report.failed.keys() - self._failed):
            _LOGGER.warning("Failed to read %s: %s", name, report.failed[name])
        self._failed = frozenset(report.failed)

        return report

    @cached_property
    def device_info(self) -> DeviceInfo:
        """Describe the inverter to the device registry."""
        info = self.device.info
        assert info is not None
        return DeviceInfo(
            identifiers={(DOMAIN, info.serial_number)},
            manufacturer=MANUFACTURER,
            model=info.model,
            sw_version=info.firmware,
            serial_number=info.serial_number,
        )
