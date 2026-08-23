"""Writing to the inverter through the control entities."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from homeassistant.components.number import (
    ATTR_VALUE,
    SERVICE_SET_VALUE,
)
from homeassistant.components.number import (
    DOMAIN as NUMBER_DOMAIN,
)
from homeassistant.components.select import (
    ATTR_OPTION,
    SERVICE_SELECT_OPTION,
)
from homeassistant.components.select import (
    DOMAIN as SELECT_DOMAIN,
)
from homeassistant.components.switch import DOMAIN as SWITCH_DOMAIN
from homeassistant.const import ATTR_ENTITY_ID, SERVICE_TURN_OFF, SERVICE_TURN_ON
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er
from modbus_connection import IllegalDataValueError

from .conftest import InverterServer

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from pytest_homeassistant_custom_component.common import MockConfigEntry

LIMIT_NUMBER = "number.blueplanet_8_6_tl3_int_power_limit"
LIMIT_SWITCH = "switch.blueplanet_8_6_tl3_int_limit_power_output"
LIMIT_SENSOR = "sensor.blueplanet_8_6_tl3_int_power_limit"
MODE_SELECT = "select.blueplanet_8_6_tl3_int_reactive_power_mode"


@pytest.fixture
async def controls(
    hass: HomeAssistant, loaded_entry: MockConfigEntry, inverter: InverterServer
) -> MockConfigEntry:
    """The entry, with the opt-in control entities switched on."""
    registry = er.async_get(hass)
    for entry in er.async_entries_for_config_entry(registry, loaded_entry.entry_id):
        if entry.domain in ("number", "switch", "select"):
            registry.async_update_entity(entry.entity_id, disabled_by=None)

    await hass.config_entries.async_reload(loaded_entry.entry_id)
    await hass.async_block_till_done()
    return loaded_entry


async def test_setting_a_power_limit(hass: HomeAssistant, controls: MockConfigEntry) -> None:
    """The written value reaches the device and comes back on the next read."""
    await hass.services.async_call(
        NUMBER_DOMAIN,
        SERVICE_SET_VALUE,
        {ATTR_ENTITY_ID: LIMIT_NUMBER, ATTR_VALUE: 50},
        blocking=True,
    )
    await hass.async_block_till_done()

    assert hass.states.get(LIMIT_NUMBER).state == "50.0"
    assert hass.states.get(LIMIT_SENSOR).state == "50.0"


async def test_enabling_and_clearing_curtailment(
    hass: HomeAssistant, controls: MockConfigEntry
) -> None:
    """Turning the limit off leaves the setpoint alone, ready to re-enable."""
    await hass.services.async_call(
        NUMBER_DOMAIN,
        SERVICE_SET_VALUE,
        {ATTR_ENTITY_ID: LIMIT_NUMBER, ATTR_VALUE: 40},
        blocking=True,
    )
    await hass.services.async_call(
        SWITCH_DOMAIN, SERVICE_TURN_ON, {ATTR_ENTITY_ID: LIMIT_SWITCH}, blocking=True
    )
    await hass.async_block_till_done()
    assert hass.states.get(LIMIT_SWITCH).state == "on"

    await hass.services.async_call(
        SWITCH_DOMAIN, SERVICE_TURN_OFF, {ATTR_ENTITY_ID: LIMIT_SWITCH}, blocking=True
    )
    await hass.async_block_till_done()

    assert hass.states.get(LIMIT_SWITCH).state == "off"
    assert hass.states.get(LIMIT_NUMBER).state == "40.0"


async def test_a_rejected_write_is_reported(
    hass: HomeAssistant, controls: MockConfigEntry, inverter: InverterServer
) -> None:
    """An inverter refusing a value must surface, not fail silently."""
    # Offset 5 of model 123 is WMaxLimPct, the register the number writes.
    inverter.unit.fail_write(inverter.address_of(123, 5), IllegalDataValueError())

    with pytest.raises(HomeAssistantError, match="rejected the change"):
        await hass.services.async_call(
            NUMBER_DOMAIN,
            SERVICE_SET_VALUE,
            {ATTR_ENTITY_ID: LIMIT_NUMBER, ATTR_VALUE: 50},
            blocking=True,
        )


async def test_the_grid_connection_switch_reads_the_device(
    hass: HomeAssistant, controls: MockConfigEntry
) -> None:
    """The captured inverter is connected, so the switch starts on."""
    assert hass.states.get("switch.blueplanet_8_6_tl3_int_grid_connection").state == "on"


async def test_reactive_power_mode(hass: HomeAssistant, controls: MockConfigEntry) -> None:
    """The captured inverter is in percent-of-WMax mode."""
    state = hass.states.get("select.blueplanet_8_6_tl3_int_reactive_power_mode")
    assert state is not None
    assert state.state == "wmax"


async def test_changing_the_reactive_power_mode(
    hass: HomeAssistant, controls: MockConfigEntry
) -> None:
    """The setpoint is re-applied, because it means something different in
    each mode — writing the mode alone would silently change what the
    inverter is being asked to do.
    """
    await hass.services.async_call(
        SELECT_DOMAIN,
        SERVICE_SELECT_OPTION,
        {ATTR_ENTITY_ID: MODE_SELECT, ATTR_OPTION: "varmax"},
        blocking=True,
    )
    await hass.async_block_till_done()

    assert hass.states.get(MODE_SELECT).state == "varmax"


async def test_a_rejected_mode_change_is_reported(
    hass: HomeAssistant, controls: MockConfigEntry, inverter: InverterServer
) -> None:
    # Offset 21 of model 123 is VArPct_Mod.
    inverter.unit.fail_write(inverter.address_of(123, 21), IllegalDataValueError())

    with pytest.raises(HomeAssistantError, match="rejected the change"):
        await hass.services.async_call(
            SELECT_DOMAIN,
            SERVICE_SELECT_OPTION,
            {ATTR_ENTITY_ID: MODE_SELECT, ATTR_OPTION: "varmax"},
            blocking=True,
        )
