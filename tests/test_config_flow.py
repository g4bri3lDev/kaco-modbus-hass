"""Adding an inverter."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.config_entries import SOURCE_USER
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.data_entry_flow import FlowResultType
from modbus_connection import ModbusTimeoutError

from custom_components.kaco.const import CONF_UNIT_ID, DOMAIN

from .conftest import InverterServer

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from pytest_homeassistant_custom_component.common import MockConfigEntry

USER_INPUT = {CONF_HOST: "192.0.2.10", CONF_PORT: 502, CONF_UNIT_ID: 1}


async def test_a_successful_setup(
    hass: HomeAssistant, inverter: InverterServer
) -> None:
    """The inverter names the entry and its serial becomes the unique id."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], USER_INPUT
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "blueplanet 8.6 TL3 INT"
    assert result["data"] == USER_INPUT
    assert result["result"].unique_id == "8.6TL01736586"


async def test_nothing_at_that_address(
    hass: HomeAssistant, inverter: InverterServer
) -> None:
    """A wrong address is recoverable: the form comes back with an error."""
    inverter.fail(ModbusTimeoutError("no answer"))

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], USER_INPUT
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}


async def test_something_that_is_not_a_sunspec_device(
    hass: HomeAssistant, inverter: InverterServer
) -> None:
    """A Modbus device that is not an inverter is named as such."""
    inverter.registers = dict.fromkeys(range(40000, 40010), 0)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], USER_INPUT
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "not_a_kaco_inverter"}


async def test_recovering_after_a_failure(
    hass: HomeAssistant, inverter: InverterServer
) -> None:
    """Fixing the address and resubmitting must work without starting over."""
    inverter.fail(ModbusTimeoutError("no answer"))

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], USER_INPUT
    )
    assert result["errors"] == {"base": "cannot_connect"}

    inverter.fail(None)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], USER_INPUT
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY


async def test_the_same_inverter_twice(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    inverter: InverterServer,
) -> None:
    """Matched on serial, so a second address for one inverter is refused."""
    config_entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {**USER_INPUT, CONF_HOST: "192.0.2.99"}
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"
