"""End-to-end: set up the entry and read sensor states."""


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
