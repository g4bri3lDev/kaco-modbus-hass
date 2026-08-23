"""Setting the entry up, and what happens when the inverter stops answering."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.config_entries import ConfigEntryState
from homeassistant.helpers import device_registry as dr
from modbus_connection import ModbusTimeoutError

from custom_components.kaco.const import DOMAIN

from .conftest import InverterServer

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from pytest_homeassistant_custom_component.common import MockConfigEntry


async def test_setup(hass: HomeAssistant, loaded_entry: MockConfigEntry) -> None:
    assert loaded_entry.state is ConfigEntryState.LOADED


async def test_device_registry_entry(hass: HomeAssistant, loaded_entry: MockConfigEntry) -> None:
    """The device is identified by serial, which survives an address change."""
    registry = dr.async_get(hass)
    device = registry.async_get_device(identifiers={(DOMAIN, "8.6TL01736586")})

    assert device is not None
    assert device.manufacturer == "KACO new energy"
    assert device.model == "blueplanet 8.6 TL3 INT"
    assert device.sw_version == "V5.53"


async def test_unload(hass: HomeAssistant, loaded_entry: MockConfigEntry) -> None:
    assert await hass.config_entries.async_unload(loaded_entry.entry_id)
    await hass.async_block_till_done()
    assert loaded_entry.state is ConfigEntryState.NOT_LOADED


async def test_a_silent_inverter_retries_rather_than_failing(
    hass: HomeAssistant,
    config_entry: MockConfigEntry,
    inverter: InverterServer,
) -> None:
    """An inverter asleep at setup time should be retried, not given up on."""
    inverter.fail(ModbusTimeoutError("asleep"))
    config_entry.add_to_hass(hass)

    assert not await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    assert config_entry.state is ConfigEntryState.SETUP_RETRY
