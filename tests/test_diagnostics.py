"""Diagnostics: useful enough to debug with, safe enough to paste in an issue."""

from __future__ import annotations

from typing import TYPE_CHECKING

from kaco_modbus.testing import BASE_ADDRESS

from custom_components.kaco.diagnostics import async_get_config_entry_diagnostics

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from pytest_homeassistant_custom_component.common import MockConfigEntry

SERIAL = "8.6TL01736586"


async def test_it_describes_the_device(
    hass: HomeAssistant, loaded_entry: MockConfigEntry
) -> None:
    result = await async_get_config_entry_diagnostics(hass, loaded_entry)

    assert result["device"]["model"] == "blueplanet 8.6 TL3 INT"
    assert result["device"]["firmware"] == "V5.53"
    assert result["device"]["base_address"] == BASE_ADDRESS
    assert result["device"]["strings"] == 2
    assert 103 in result["device"]["models"]


async def test_it_reports_what_was_read(
    hass: HomeAssistant, loaded_entry: MockConfigEntry
) -> None:
    result = await async_get_config_entry_diagnostics(hass, loaded_entry)

    assert "inverter" in result["readings"]["updated"]
    assert result["readings"]["failed"] == {}


async def test_the_registers_can_be_replayed(
    hass: HomeAssistant, loaded_entry: MockConfigEntry
) -> None:
    """The point of the dump: reproducing a report without the hardware."""
    result = await async_get_config_entry_diagnostics(hass, loaded_entry)

    registers = result["registers"]["holding"]
    assert len(registers) > 100
    assert all(isinstance(address, int) for address in registers)


class TestRedaction:
    """Anything identifying gets stripped, including from the raw registers."""

    async def test_the_serial_is_redacted(
        self, hass: HomeAssistant, loaded_entry: MockConfigEntry
    ) -> None:
        result = await async_get_config_entry_diagnostics(hass, loaded_entry)
        assert result["device"]["serial_number"] != SERIAL

    async def test_the_host_is_redacted(
        self, hass: HomeAssistant, loaded_entry: MockConfigEntry
    ) -> None:
        result = await async_get_config_entry_diagnostics(hass, loaded_entry)
        assert result["entry"]["host"] != "192.0.2.10"

    async def test_the_serial_is_not_recoverable_from_the_registers(
        self, hass: HomeAssistant, loaded_entry: MockConfigEntry
    ) -> None:
        """Redacting the field is pointless if model 1 still carries it."""
        result = await async_get_config_entry_diagnostics(hass, loaded_entry)

        registers = result["registers"]["holding"]
        decoded = b"".join(
            value.to_bytes(2, "big") for _, value in sorted(registers.items())
        )
        assert SERIAL.encode() not in decoded
