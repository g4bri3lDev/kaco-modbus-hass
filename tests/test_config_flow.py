"""Adding an inverter."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest
from homeassistant.config_entries import SOURCE_USER
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.exceptions import HomeAssistantError
from kaco_modbus.testing import BLUEPLANET_86TL3, with_manufacturer
from modbus_connection import ModbusTimeoutError

from custom_components.kaco_modbus.const import CONF_UNIT_ID, DOMAIN

from .conftest import FLOW_GET_UNIT, InverterServer

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from pytest_homeassistant_custom_component.common import MockConfigEntry

USER_INPUT = {CONF_HOST: "192.0.2.10", CONF_PORT: 502, CONF_UNIT_ID: 1}


async def test_a_successful_setup(hass: HomeAssistant, inverter: InverterServer) -> None:
    """The inverter names the entry and its serial becomes the unique id."""
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(result["flow_id"], USER_INPUT)
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "blueplanet 8.6 TL3 INT"
    assert result["data"] == USER_INPUT
    assert result["result"].unique_id == "8.6TL00000000"


async def test_nothing_at_that_address(hass: HomeAssistant, inverter: InverterServer) -> None:
    """A wrong address is recoverable: the form comes back with an error."""
    inverter.fail(ModbusTimeoutError("no answer"))

    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], USER_INPUT)

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}


@pytest.mark.parametrize(
    ("registers", "error"),
    [
        pytest.param(
            # Another vendor answers the same SunSpec models at the same
            # addresses, so only its manufacturer tells it apart.
            with_manufacturer(BLUEPLANET_86TL3, "Fronius"),
            "not_a_kaco_inverter",
            id="another_brand",
        ),
        pytest.param(
            dict.fromkeys(range(40000, 40010), 0),
            "not_a_sunspec_inverter",
            id="not_sunspec",
        ),
    ],
)
async def test_something_that_is_not_a_kaco(
    hass: HomeAssistant,
    inverter: InverterServer,
    registers: dict[int, int],
    error: str,
) -> None:
    """A device that answers but is not a KACO inverter is named as such."""
    inverter.registers = registers

    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], USER_INPUT)

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": error}


@pytest.mark.parametrize(
    ("raised", "error"),
    [
        pytest.param(HomeAssistantError("in use"), "already_in_use", id="already_in_use"),
        pytest.param(RuntimeError("boom"), "unknown", id="unexpected"),
    ],
)
@pytest.mark.usefixtures("inverter")
async def test_borrowing_the_unit_fails(hass: HomeAssistant, raised: Exception, error: str) -> None:
    """A failure before the inverter is even reached still shows on the form."""
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    with patch(FLOW_GET_UNIT, side_effect=raised):
        result = await hass.config_entries.flow.async_configure(result["flow_id"], USER_INPUT)

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": error}


async def test_recovering_after_a_failure(hass: HomeAssistant, inverter: InverterServer) -> None:
    """Fixing the address and resubmitting must work without starting over."""
    inverter.fail(ModbusTimeoutError("no answer"))

    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], USER_INPUT)
    assert result["errors"] == {"base": "cannot_connect"}

    inverter.fail(None)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], USER_INPUT)
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY


async def test_the_same_inverter_twice(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    inverter: InverterServer,
) -> None:
    """Matched on serial, so a second address for one inverter is refused."""
    config_entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {**USER_INPUT, CONF_HOST: "192.0.2.99"}
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
