"""The two failure paths the coordinator exists to handle."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, patch

from freezegun.api import FrozenDateTimeFactory
from homeassistant.const import STATE_UNAVAILABLE
from kaco_modbus import SunSpecMapShiftError
from modbus_connection import ModbusTimeoutError
from pytest_homeassistant_custom_component.common import async_fire_time_changed

from custom_components.kaco.const import READINGS_INTERVAL, TIMEOUTS_BEFORE_DISCONNECT

from .conftest import InverterServer

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from pytest_homeassistant_custom_component.common import MockConfigEntry

POWER = "sensor.blueplanet_8_6_tl3_int_ac_power"


async def _poll(hass: HomeAssistant, freezer: FrozenDateTimeFactory) -> None:
    """Advance to the next readings poll."""
    freezer.tick(READINGS_INTERVAL)
    async_fire_time_changed(hass)
    await hass.async_block_till_done()


async def test_a_moved_sunspec_map_reloads_the_entry(
    hass: HomeAssistant,
    loaded_entry: MockConfigEntry,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Every bound register offset is stale, so only rediscovery fixes it.

    SunSpecMapShiftError is not a ModbusError, so it needs its own handling —
    without it the integration would keep reading the wrong registers and
    reporting plausible nonsense.
    """
    # The coordinator captured the bound method at construction, so patch the
    # coordinator's own reference rather than the device attribute.
    coordinator = loaded_entry.runtime_data.readings

    with (
        patch.object(coordinator, "_poll", side_effect=SunSpecMapShiftError("moved")),
        patch.object(hass.config_entries, "async_schedule_reload") as reload,
    ):
        await _poll(hass, freezer)

    reload.assert_called_once_with(loaded_entry.entry_id)


async def test_a_stuck_link_is_dropped_after_three_timeouts(
    hass: HomeAssistant,
    loaded_entry: MockConfigEntry,
    inverter: InverterServer,
    freezer: FrozenDateTimeFactory,
) -> None:
    """An inverter asleep after dark accepts TCP but answers nothing.

    The socket looks alive, so nothing else would ever reopen it.
    """
    connection = inverter.connections[-1]
    inverter.fail(ModbusTimeoutError("asleep"))

    with patch.object(connection, "disconnect", AsyncMock()) as disconnect:
        for _ in range(TIMEOUTS_BEFORE_DISCONNECT - 1):
            await _poll(hass, freezer)
        assert not disconnect.called, "dropped the link too eagerly"

        await _poll(hass, freezer)
        disconnect.assert_awaited_once()


async def test_the_timeout_count_resets_on_a_good_poll(
    hass: HomeAssistant,
    loaded_entry: MockConfigEntry,
    inverter: InverterServer,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Occasional timeouts must not eventually drop a healthy connection."""
    connection = inverter.connections[-1]

    with patch.object(connection, "disconnect", AsyncMock()) as disconnect:
        for _ in range(TIMEOUTS_BEFORE_DISCONNECT - 1):
            inverter.fail(ModbusTimeoutError("blip"))
            await _poll(hass, freezer)
            inverter.fail(None)
            await _poll(hass, freezer)

        assert not disconnect.called


async def test_a_partial_failure_still_publishes_what_worked(
    hass: HomeAssistant,
    loaded_entry: MockConfigEntry,
    inverter: InverterServer,
    freezer: FrozenDateTimeFactory,
) -> None:
    """One broken block must not take out every sensor."""
    model = inverter.address_of(160, 0)
    for address in range(model, model + 50):
        inverter.unit.fail_read(address, ModbusTimeoutError("slow block"))

    await _poll(hass, freezer)

    assert hass.states.get(POWER).state == "1000"
    assert hass.states.get("sensor.blueplanet_8_6_tl3_int_string_1_power").state == (
        STATE_UNAVAILABLE
    )
