"""Fixtures backed by the register image captured from a real inverter."""

from __future__ import annotations

from collections.abc import Generator
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

# Where the integration builds its connection. Patching here rather than inside
# the library keeps the test honest: everything below this point is real code
# talking to a real, in-memory register map.
CONNECTION = "custom_components.kaco_modbus.ModbusConnection"
FLOW_CONNECTION = "custom_components.kaco_modbus.config_flow.ModbusConnection"


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
    with patch(CONNECTION, new=server), patch(FLOW_CONNECTION, new=server):
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
