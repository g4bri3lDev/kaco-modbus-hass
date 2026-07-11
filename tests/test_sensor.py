"""End-to-end: set up the entry and read sensor states."""

from homeassistant.helpers import entity_registry as er


async def test_sensors_report_values(hass, mock_unit, config_entry):
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get("sensor.kaco_new_energy_blueplanet_8_6_tl3_ac_power")
    assert state is not None
    assert float(state.state) == 3280.0

    energy = hass.states.get(
        "sensor.kaco_new_energy_blueplanet_8_6_tl3_lifetime_energy"
    )
    assert energy is not None
    assert float(energy.state) == 8883.0  # kWh after suggested unit conversion

    operating = hass.states.get(
        "sensor.kaco_new_energy_blueplanet_8_6_tl3_operating_state"
    )
    assert operating is not None
    assert operating.state == "mppt"


async def test_no_mppt_no_string_sensors(hass, mock_unit, config_entry):
    """The synthetic fixture has no model 160 -- no per-string sensors."""
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    entity_ids = hass.states.async_entity_ids("sensor")
    assert entity_ids  # sanity: setup did produce sensors
    assert not any("string_" in entity_id for entity_id in entity_ids)


async def test_mppt_string_sensors(hass, mock_unit_real, config_entry):
    """A real dump with 2 MPPT strings gets one power sensor per string."""
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    entity_ids = sorted(
        entity_id
        for entity_id in hass.states.async_entity_ids("sensor")
        if "string_" in entity_id
    )
    power_ids = [e for e in entity_ids if e.endswith("_power")]
    assert len(power_ids) == 2

    string_1 = next(e for e in power_ids if "string_1_" in e)
    string_2 = next(e for e in power_ids if "string_2_" in e)

    state_1 = hass.states.get(string_1)
    state_2 = hass.states.get(string_2)
    assert state_1 is not None
    assert state_2 is not None
    assert float(state_1.state) == 2020.0
    assert float(state_2.state) == 2230.0

    # Disabled-by-default sensors (voltage/current/energy) don't get states,
    # but their unique_ids should still be registered.
    registry = er.async_get(hass)
    entry = hass.config_entries.async_entries("kaco")[0]
    serial = entry.runtime_data.device.probe.serial
    for suffix in (
        "mppt_1_dc_voltage",
        "mppt_1_dc_current",
        "mppt_1_dc_energy",
        "mppt_2_dc_voltage",
        "mppt_2_dc_current",
        "mppt_2_dc_energy",
    ):
        unique_id = f"{serial}_{suffix}"
        assert registry.async_get_entity_id("sensor", "kaco", unique_id) is not None
