"""Fixtures backed by the register image captured from a real inverter."""

from __future__ import annotations

from collections.abc import Generator
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Any
from unittest.mock import patch

import pytest
from homeassistant.const import CONF_HOST, CONF_PORT
from kaco_modbus.testing import BASE_ADDRESS, BLUEPLANET_86TL3
from modbus_connection.mock import MockModbusConnection
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.kaco_modbus.const import CONF_UNIT_ID, DOMAIN

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

# Setup takes its unit from the modbus integration; the config flow borrows a
# temporary one. Patching at these two seams keeps everything below them real
# code talking to a real, in-memory register map.
GET_UNIT = "custom_components.kaco_modbus.async_get_unit"
FLOW_GET_UNIT = "custom_components.kaco_modbus.config_flow.async_get_temporary_unit"


class InverterServer:
    """Hands out a fresh connection per call, over one register image.

    A new connection each time is what production does — the config flow opens
    one to probe and closes it again — so a single shared mock would wrongly
    make the second attempt fail on a closed client.
    """

    def __init__(self) -> None:
        self.registers: dict[int, int] = dict(BLUEPLANET_86TL3)
        self.failure: Exception | None = None
        self.connections: list[MockModbusConnection] = []

    def __call__(self, *args: Any, **kwargs: Any) -> MockModbusConnection:
        connection = MockModbusConnection()
        unit = connection.for_unit(1)
        unit.load_raw({"holding": self.registers})
        if self.failure is not None:
            unit.fail_requests(self.failure)
        self.connections.append(connection)
        return connection

    def fail(self, error: Exception | None) -> None:
        """Make every read fail, on existing connections and future ones."""
        self.failure = error
        for connection in self.connections:
            connection.for_unit(1).fail_requests(error)

    @property
    def unit(self) -> Any:
        """The unit of the most recently opened connection."""
        return self.connections[-1].for_unit(1)

    def address_of(self, model_id: int, offset: int) -> int:
        """The absolute address of one field, by walking the captured chain.

        Offsets in the generated components are relative to the model header
        and already count its two registers, so this is a plain addition.
        """
        address = BASE_ADDRESS + 2
        while (found := self.registers[address]) != 0xFFFF:
            if found == model_id:
                return address + offset
            address += 2 + self.registers[address + 1]
        raise KeyError(f"model {model_id} is not in the image")


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Let Home Assistant load custom_components/kaco_modbus."""


@pytest.fixture
def inverter() -> Generator[InverterServer]:
    """A mock inverter serving the real 8.6 TL3 register image."""
    server = InverterServer()

    def get_unit(hass: Any, entry: Any, params: Any, unit_id: int) -> Any:
        """Stand in for the modbus integration handing out a unit.

        It owns the connection there, so unlike the old config-flow path
        nothing is closed on this side.
        """
        return server().for_unit(unit_id)

    @asynccontextmanager
    async def temporary_unit(hass: Any, params: Any, unit_id: int) -> Any:
        """Stand in for the config flow borrowing a unit for a probe."""
        connection = server()
        try:
            yield connection.for_unit(unit_id)
        finally:
            await connection.close()

    with patch(GET_UNIT, new=get_unit), patch(FLOW_GET_UNIT, new=temporary_unit):
        yield server


@pytest.fixture
def config_entry() -> MockConfigEntry:
    """A config entry pointing at the mock inverter."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="blueplanet 8.6 TL3 INT",
        unique_id="8.6TL00000000",
        data={CONF_HOST: "192.0.2.10", CONF_PORT: 502, CONF_UNIT_ID: 1},
    )


@pytest.fixture
async def loaded_entry(
    hass: HomeAssistant, config_entry: MockConfigEntry, inverter: InverterServer
) -> MockConfigEntry:
    """A fully set-up integration."""
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    return config_entry
