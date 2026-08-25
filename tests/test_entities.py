"""What the entities show, and what happens when the inverter goes quiet."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from freezegun.api import FrozenDateTimeFactory
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.helpers import entity_registry as er
from kaco_modbus.testing import BLUEPLANET_86TL3_ASLEEP
from modbus_connection import ModbusTimeoutError
from pytest_homeassistant_custom_component.common import async_fire_time_changed

from custom_components.kaco_modbus.const import READINGS_INTERVAL

from .conftest import InverterServer

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from pytest_homeassistant_custom_component.common import MockConfigEntry

POWER = "sensor.blueplanet_8_6_tl3_int_ac_power"
ENERGY = "sensor.blueplanet_8_6_tl3_int_total_energy_produced"
STRING_1 = "sensor.blueplanet_8_6_tl3_int_string_1_power"


@pytest.mark.parametrize(
    ("entity_id", "expected"),
    [
        (POWER, "1000"),
        ("sensor.blueplanet_8_6_tl3_int_dc_power", "1020"),
        ("sensor.blueplanet_8_6_tl3_int_grid_frequency", "49.944"),
        ("sensor.blueplanet_8_6_tl3_int_temperature", "46.9"),
        ("sensor.blueplanet_8_6_tl3_int_voltage_l1", "226.5"),
        ("sensor.blueplanet_8_6_tl3_int_operating_state", "mppt"),
        (STRING_1, "360"),
        ("sensor.blueplanet_8_6_tl3_int_string_2_power", "650"),
        (ENERGY, "12187.169"),
    ],
)
async def test_sensor_values(
    hass: HomeAssistant, loaded_entry: MockConfigEntry, entity_id: str, expected: str
) -> None:
    """Values reach Home Assistant scaled and in the right unit."""
    state = hass.states.get(entity_id)
    assert state is not None, f"{entity_id} was not created"
    assert state.state == expected


async def test_one_string_per_mppt_input(
    hass: HomeAssistant, loaded_entry: MockConfigEntry
) -> None:
    """This inverter has two strings, so there is no string 3."""
    assert hass.states.get(STRING_1) is not None
    assert hass.states.get("sensor.blueplanet_8_6_tl3_int_string_3_power") is None


async def test_controls_are_opt_in(hass: HomeAssistant, loaded_entry: MockConfigEntry) -> None:
    """Nothing that writes to a live inverter is enabled without asking."""
    registry = er.async_get(hass)
    writable = [
        entry
        for entry in er.async_entries_for_config_entry(registry, loaded_entry.entry_id)
        if entry.domain in ("number", "switch", "select")
    ]

    assert writable, "the control entities should exist"
    assert all(entry.disabled_by is er.RegistryEntryDisabler.INTEGRATION for entry in writable)


class TestWhenTheInverterSleeps:
    """After dark a grid-tied inverter accepts TCP but answers nothing."""

    async def test_readings_go_unavailable(
        self,
        hass: HomeAssistant,
        loaded_entry: MockConfigEntry,
        inverter: InverterServer,
        freezer: FrozenDateTimeFactory,
    ) -> None:
        inverter.fail(ModbusTimeoutError("asleep"))
        freezer.tick(READINGS_INTERVAL)
        async_fire_time_changed(hass)
        await hass.async_block_till_done()

        assert hass.states.get(POWER).state == STATE_UNAVAILABLE

    async def test_lifetime_energy_holds_its_value(
        self,
        hass: HomeAssistant,
        loaded_entry: MockConfigEntry,
        inverter: InverterServer,
        freezer: FrozenDateTimeFactory,
    ) -> None:
        """It is a long-term statistic: going unavailable every night would
        leave a gap in the Energy dashboard.
        """
        inverter.fail(ModbusTimeoutError("asleep"))
        freezer.tick(READINGS_INTERVAL)
        async_fire_time_changed(hass)
        await hass.async_block_till_done()

        assert hass.states.get(ENERGY).state == "12187.169"

    async def test_it_comes_back_at_sunrise(
        self,
        hass: HomeAssistant,
        loaded_entry: MockConfigEntry,
        inverter: InverterServer,
        freezer: FrozenDateTimeFactory,
    ) -> None:
        """Recovery must not need a reload."""
        inverter.fail(ModbusTimeoutError("asleep"))
        freezer.tick(READINGS_INTERVAL)
        async_fire_time_changed(hass)
        await hass.async_block_till_done()
        assert hass.states.get(POWER).state == STATE_UNAVAILABLE

        inverter.fail(None)
        freezer.tick(READINGS_INTERVAL)
        async_fire_time_changed(hass)
        await hass.async_block_till_done()

        assert hass.states.get(POWER).state == "1000"


class TestAsleep:
    """What Home Assistant shows once the sun goes down.

    The inverter keeps answering, so nothing goes unavailable — but the
    readings it stops taking must not be published as plausible-looking
    zeros. See kaco-modbus docs/quirks.md.
    """

    @pytest.fixture(autouse=True)
    def _asleep(self, inverter: InverterServer) -> None:
        inverter.registers = dict(BLUEPLANET_86TL3_ASLEEP)

    @pytest.mark.parametrize(
        "entity_id",
        [
            "sensor.blueplanet_8_6_tl3_int_grid_frequency",
            "sensor.blueplanet_8_6_tl3_int_voltage_l1",
            "sensor.blueplanet_8_6_tl3_int_voltage_l2",
            "sensor.blueplanet_8_6_tl3_int_voltage_l3",
            "sensor.blueplanet_8_6_tl3_int_temperature",
        ],
    )
    async def test_unmeasured_readings_are_withheld(
        self, hass: HomeAssistant, loaded_entry: MockConfigEntry, entity_id: str
    ) -> None:
        """0 Hz and 0 V would look like a grid outage every night."""
        state = hass.states.get(entity_id)
        assert state is not None
        assert state.state == STATE_UNKNOWN

    @pytest.mark.parametrize(
        ("entity_id", "expected"),
        [
            ("sensor.blueplanet_8_6_tl3_int_ac_power", "0"),
            ("sensor.blueplanet_8_6_tl3_int_dc_power", "0"),
            ("sensor.blueplanet_8_6_tl3_int_string_1_power", "0"),
        ],
    )
    async def test_genuine_zeros_are_kept(
        self,
        hass: HomeAssistant,
        loaded_entry: MockConfigEntry,
        entity_id: str,
        expected: str,
    ) -> None:
        """Producing nothing really is zero, and must still be reported."""
        assert hass.states.get(entity_id).state == expected

    async def test_it_reports_sleeping(
        self, hass: HomeAssistant, loaded_entry: MockConfigEntry
    ) -> None:
        state = hass.states.get("sensor.blueplanet_8_6_tl3_int_operating_state")
        assert state.state == "sleeping"

    async def test_lifetime_energy_still_reports(
        self, hass: HomeAssistant, loaded_entry: MockConfigEntry
    ) -> None:
        """The Energy dashboard must not gain a gap overnight."""
        state = hass.states.get(ENERGY)
        assert state.state not in (STATE_UNKNOWN, STATE_UNAVAILABLE)
        assert float(state.state) > 12000
