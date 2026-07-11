"""Sensors for a KACO inverter."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    EntityCategory,
    UnitOfApparentPower,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfFrequency,
    UnitOfPower,
    UnitOfReactivePower,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType
from kaco_modbus import KacoInverter, OperatingState

from .coordinator import KacoConfigEntry, KacoCoordinator
from .entity import KacoEntity


@dataclass(frozen=True, kw_only=True)
class KacoSensorDescription(SensorEntityDescription):
    """Describes one KACO sensor."""

    value_fn: Callable[[KacoInverter], StateType]
    translation_placeholders: dict[str, str] | None = None


def _state(device: KacoInverter) -> str | None:
    state = device.inverter.state
    return state.name.lower() if state is not None else None


SENSORS: tuple[KacoSensorDescription, ...] = (
    KacoSensorDescription(
        key="ac_power",
        translation_key="ac_power",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: d.inverter.ac_power,
    ),
    KacoSensorDescription(
        key="lifetime_energy",
        translation_key="lifetime_energy",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        suggested_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda d: d.inverter.energy_total,
    ),
    KacoSensorDescription(
        key="operating_state",
        translation_key="operating_state",
        device_class=SensorDeviceClass.ENUM,
        options=[s.name.lower() for s in OperatingState],
        value_fn=_state,
    ),
    KacoSensorDescription(
        key="frequency",
        translation_key="frequency",
        device_class=SensorDeviceClass.FREQUENCY,
        native_unit_of_measurement=UnitOfFrequency.HERTZ,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: d.inverter.frequency,
    ),
    KacoSensorDescription(
        key="ac_current",
        translation_key="ac_current",
        device_class=SensorDeviceClass.CURRENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: d.inverter.ac_current,
    ),
    KacoSensorDescription(
        key="voltage_phase_a",
        translation_key="voltage_phase_a",
        device_class=SensorDeviceClass.VOLTAGE,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
        value_fn=lambda d: d.inverter.voltage_phase_a,
    ),
    KacoSensorDescription(
        key="voltage_phase_b",
        translation_key="voltage_phase_b",
        device_class=SensorDeviceClass.VOLTAGE,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
        value_fn=lambda d: d.inverter.voltage_phase_b,
    ),
    KacoSensorDescription(
        key="voltage_phase_c",
        translation_key="voltage_phase_c",
        device_class=SensorDeviceClass.VOLTAGE,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
        value_fn=lambda d: d.inverter.voltage_phase_c,
    ),
    KacoSensorDescription(
        key="dc_power",
        translation_key="dc_power",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: d.inverter.dc_power,
    ),
    KacoSensorDescription(
        key="dc_voltage",
        translation_key="dc_voltage",
        device_class=SensorDeviceClass.VOLTAGE,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
        value_fn=lambda d: d.inverter.dc_voltage,
    ),
    KacoSensorDescription(
        key="dc_current",
        translation_key="dc_current",
        device_class=SensorDeviceClass.CURRENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
        value_fn=lambda d: d.inverter.dc_current,
    ),
    KacoSensorDescription(
        key="apparent_power",
        translation_key="apparent_power",
        device_class=SensorDeviceClass.APPARENT_POWER,
        native_unit_of_measurement=UnitOfApparentPower.VOLT_AMPERE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
        value_fn=lambda d: d.inverter.apparent_power,
    ),
    KacoSensorDescription(
        key="reactive_power",
        translation_key="reactive_power",
        device_class=SensorDeviceClass.REACTIVE_POWER,
        native_unit_of_measurement=UnitOfReactivePower.VOLT_AMPERE_REACTIVE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
        value_fn=lambda d: d.inverter.reactive_power,
    ),
    KacoSensorDescription(
        key="temperature_cabinet",
        translation_key="temperature_cabinet",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: d.inverter.temperature_cabinet,
    ),
    KacoSensorDescription(
        key="temperature_heatsink",
        translation_key="temperature_heatsink",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: d.inverter.temperature_heatsink,
    ),
)


def _mppt_value(module_index: int, attr: str) -> Callable[[KacoInverter], StateType]:
    """Read one attribute of one MPPT module, tolerating a shrunk tuple."""

    def _value(device: KacoInverter) -> StateType:
        if module_index >= len(device.mppt_modules):
            return None
        return getattr(device.mppt_modules[module_index], attr)

    return _value


def _mppt_descriptions(device: KacoInverter) -> tuple[KacoSensorDescription, ...]:
    """Per-string sensors for each MPPT module the device advertises."""
    descriptions: list[KacoSensorDescription] = []
    for module_index in range(len(device.mppt_modules)):
        i = module_index + 1
        placeholders = {"index": str(i)}
        descriptions.extend(
            (
                KacoSensorDescription(
                    key=f"mppt_{i}_dc_power",
                    translation_key="mppt_dc_power",
                    translation_placeholders=placeholders,
                    device_class=SensorDeviceClass.POWER,
                    native_unit_of_measurement=UnitOfPower.WATT,
                    state_class=SensorStateClass.MEASUREMENT,
                    value_fn=_mppt_value(module_index, "dc_power"),
                ),
                KacoSensorDescription(
                    key=f"mppt_{i}_dc_voltage",
                    translation_key="mppt_dc_voltage",
                    translation_placeholders=placeholders,
                    device_class=SensorDeviceClass.VOLTAGE,
                    native_unit_of_measurement=UnitOfElectricPotential.VOLT,
                    state_class=SensorStateClass.MEASUREMENT,
                    entity_registry_enabled_default=False,
                    value_fn=_mppt_value(module_index, "dc_voltage"),
                ),
                KacoSensorDescription(
                    key=f"mppt_{i}_dc_current",
                    translation_key="mppt_dc_current",
                    translation_placeholders=placeholders,
                    device_class=SensorDeviceClass.CURRENT,
                    native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
                    state_class=SensorStateClass.MEASUREMENT,
                    entity_registry_enabled_default=False,
                    value_fn=_mppt_value(module_index, "dc_current"),
                ),
                KacoSensorDescription(
                    key=f"mppt_{i}_dc_energy",
                    translation_key="mppt_dc_energy",
                    translation_placeholders=placeholders,
                    device_class=SensorDeviceClass.ENERGY,
                    native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
                    suggested_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
                    state_class=SensorStateClass.TOTAL_INCREASING,
                    entity_registry_enabled_default=False,
                    value_fn=_mppt_value(module_index, "dc_energy"),
                ),
            )
        )
    return tuple(descriptions)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: KacoConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up KACO sensors."""
    coordinator = entry.runtime_data
    descriptions = SENSORS + _mppt_descriptions(coordinator.device)
    async_add_entities(
        KacoSensor(coordinator, description) for description in descriptions
    )


class KacoSensor(KacoEntity, SensorEntity):
    """One value of the inverter."""

    entity_description: KacoSensorDescription

    def __init__(
        self, coordinator: KacoCoordinator, description: KacoSensorDescription
    ) -> None:
        super().__init__(coordinator, description)
        if description.translation_placeholders is not None:
            self._attr_translation_placeholders = description.translation_placeholders

    @property
    def native_value(self) -> StateType:
        return self.entity_description.value_fn(self.coordinator.device)
