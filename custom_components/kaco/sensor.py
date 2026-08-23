"""What the inverter measures."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from homeassistant.components.sensor import (
    RestoreSensor,
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
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

from .entity import KacoEntity

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
    from homeassistant.helpers.typing import StateType
    from kaco_modbus import KacoInverter

    from . import KacoConfigEntry
    from .coordinator import KacoCoordinator


@dataclass(frozen=True, kw_only=True)
class KacoSensorDescription(SensorEntityDescription):
    """A sensor, and where to find its value on the device object."""

    value_fn: Callable[[KacoInverter], StateType]
    sub_system: str


def _inverter(name: str) -> Callable[[KacoInverter], StateType]:
    """Read a field off the inverter block."""

    def value(device: KacoInverter) -> StateType:
        return getattr(device.inverter, name, None)

    return value


SENSORS: tuple[KacoSensorDescription, ...] = (
    KacoSensorDescription(
        key="ac_power",
        translation_key="ac_power",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_inverter("w"),
        sub_system="inverter",
    ),
    KacoSensorDescription(
        key="apparent_power",
        translation_key="apparent_power",
        device_class=SensorDeviceClass.APPARENT_POWER,
        native_unit_of_measurement=UnitOfApparentPower.VOLT_AMPERE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
        value_fn=_inverter("va"),
        sub_system="inverter",
    ),
    KacoSensorDescription(
        key="reactive_power",
        translation_key="reactive_power",
        device_class=SensorDeviceClass.REACTIVE_POWER,
        native_unit_of_measurement=UnitOfReactivePower.VOLT_AMPERE_REACTIVE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
        value_fn=_inverter("v_ar"),
        sub_system="inverter",
    ),
    KacoSensorDescription(
        key="power_factor",
        translation_key="power_factor",
        device_class=SensorDeviceClass.POWER_FACTOR,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
        value_fn=_inverter("pf"),
        sub_system="inverter",
    ),
    KacoSensorDescription(
        key="frequency",
        translation_key="frequency",
        device_class=SensorDeviceClass.FREQUENCY,
        native_unit_of_measurement=UnitOfFrequency.HERTZ,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
        value_fn=_inverter("hz"),
        sub_system="inverter",
    ),
    KacoSensorDescription(
        key="ac_current",
        translation_key="ac_current",
        device_class=SensorDeviceClass.CURRENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_inverter("a"),
        sub_system="inverter",
    ),
    KacoSensorDescription(
        key="dc_power",
        translation_key="dc_power",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_inverter("dcw"),
        sub_system="inverter",
    ),
    KacoSensorDescription(
        key="dc_voltage",
        translation_key="dc_voltage",
        device_class=SensorDeviceClass.VOLTAGE,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
        value_fn=_inverter("dcv"),
        sub_system="inverter",
    ),
    KacoSensorDescription(
        key="dc_current",
        translation_key="dc_current",
        device_class=SensorDeviceClass.CURRENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
        value_fn=_inverter("dca"),
        sub_system="inverter",
    ),
    # Only the cabinet sensor is real on this firmware; the heat-sink,
    # transformer and "other" temperatures all read as not-implemented.
    KacoSensorDescription(
        key="temperature",
        translation_key="temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=_inverter("tmp_cab"),
        sub_system="inverter",
    ),
    KacoSensorDescription(
        key="operating_state",
        translation_key="operating_state",
        device_class=SensorDeviceClass.ENUM,
        options=[
            "off",
            "sleeping",
            "starting",
            "mppt",
            "throttled",
            "shutting_down",
            "fault",
            "standby",
        ],
        value_fn=lambda device: (
            state.name.lower()
            if (state := getattr(device.inverter, "st", None)) is not None
            else None
        ),
        sub_system="inverter",
    ),
)

# Phase-to-neutral only: this firmware leaves the line-to-line voltages
# unimplemented, so exposing them would give three permanently empty sensors.
PHASE_SENSORS: tuple[KacoSensorDescription, ...] = tuple(
    KacoSensorDescription(
        key=f"voltage_l{index}",
        translation_key=f"voltage_l{index}",
        device_class=SensorDeviceClass.VOLTAGE,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=_inverter(field),
        sub_system="inverter",
    )
    for index, field in ((1, "ph_vph_a"), (2, "ph_vph_b"), (3, "ph_vph_c"))
)

CURRENT_SENSORS: tuple[KacoSensorDescription, ...] = tuple(
    KacoSensorDescription(
        key=f"current_l{index}",
        translation_key=f"current_l{index}",
        device_class=SensorDeviceClass.CURRENT,
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=False,
        value_fn=_inverter(field),
        sub_system="inverter",
    )
    for index, field in ((1, "aph_a"), (2, "aph_b"), (3, "aph_c"))
)

ENERGY = KacoSensorDescription(
    key="lifetime_energy",
    translation_key="lifetime_energy",
    device_class=SensorDeviceClass.ENERGY,
    native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
    state_class=SensorStateClass.TOTAL_INCREASING,
    suggested_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
    suggested_display_precision=2,
    value_fn=_inverter("wh"),
    sub_system="inverter",
)

DIAGNOSTICS: tuple[KacoSensorDescription, ...] = (
    KacoSensorDescription(
        key="rated_power",
        translation_key="rated_power",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda device: getattr(device.nameplate, "w_rtg", None),
        sub_system="nameplate",
    ),
    KacoSensorDescription(
        key="power_limit",
        translation_key="power_limit",
        native_unit_of_measurement=PERCENTAGE,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda device: getattr(device.controls, "w_max_lim_pct", None),
        sub_system="controls",
    ),
)


@dataclass(frozen=True, kw_only=True)
class KacoStringSensorDescription(SensorEntityDescription):
    """A per-MPPT-string sensor."""

    field: str
    index: int


def _string_sensors(count: int) -> list[KacoStringSensorDescription]:
    """Build the per-string sensors for however many strings there are."""
    descriptions: list[KacoStringSensorDescription] = []
    for index in range(count):
        number = index + 1
        descriptions += [
            KacoStringSensorDescription(
                key=f"string_{number}_power",
                translation_key="string_power",
                translation_placeholders={"number": str(number)},
                device_class=SensorDeviceClass.POWER,
                native_unit_of_measurement=UnitOfPower.WATT,
                state_class=SensorStateClass.MEASUREMENT,
                field="dcw",
                index=index,
            ),
            KacoStringSensorDescription(
                key=f"string_{number}_voltage",
                translation_key="string_voltage",
                translation_placeholders={"number": str(number)},
                device_class=SensorDeviceClass.VOLTAGE,
                native_unit_of_measurement=UnitOfElectricPotential.VOLT,
                state_class=SensorStateClass.MEASUREMENT,
                suggested_display_precision=1,
                field="dcv",
                index=index,
            ),
            KacoStringSensorDescription(
                key=f"string_{number}_current",
                translation_key="string_current",
                translation_placeholders={"number": str(number)},
                device_class=SensorDeviceClass.CURRENT,
                native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
                state_class=SensorStateClass.MEASUREMENT,
                field="dca",
                index=index,
            ),
        ]
    return descriptions


async def async_setup_entry(
    hass: HomeAssistant,
    entry: KacoConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the sensors this inverter actually has."""
    data = entry.runtime_data
    readings, settings, device = data.readings, data.settings, data.device

    entities: list[SensorEntity] = [
        KacoSensor(readings, description)
        for description in (*SENSORS, *PHASE_SENSORS, *CURRENT_SENSORS)
    ]
    entities.append(KacoEnergySensor(readings, ENERGY))
    entities += [
        KacoStringSensor(readings, description)
        for description in _string_sensors(len(device.strings))
    ]
    entities += [
        KacoSensor(settings, description)
        for description in DIAGNOSTICS
        if getattr(device, description.sub_system) is not None
    ]

    async_add_entities(entities)


class KacoSensor(KacoEntity, SensorEntity):
    """A reading taken straight off the device object."""

    entity_description: KacoSensorDescription

    def __init__(self, coordinator: KacoCoordinator, description: KacoSensorDescription) -> None:
        """Set up a sensor reading from its description's sub-system."""
        super().__init__(coordinator, description, description.sub_system)

    @property
    def native_value(self) -> StateType:
        """The current reading."""
        return self.entity_description.value_fn(self.coordinator.device)


class KacoStringSensor(KacoEntity, SensorEntity):
    """A reading from one MPPT string."""

    entity_description: KacoStringSensorDescription

    def __init__(
        self, coordinator: KacoCoordinator, description: KacoStringSensorDescription
    ) -> None:
        """Set up a sensor for one string of the MPPT component."""
        super().__init__(coordinator, description, "mppt")

    @property
    def native_value(self) -> StateType:
        """The current reading, or None if the string went away."""
        strings = self.coordinator.device.strings
        if self.entity_description.index >= len(strings):
            return None
        value: Any = getattr(
            strings[self.entity_description.index], self.entity_description.field, None
        )
        return value  # type: ignore[no-any-return]


class KacoEnergySensor(KacoEntity, RestoreSensor):
    """Lifetime energy: a long-term statistic that outlives the inverter.

    Grid-tied inverters stop answering after dark. A total that went
    unavailable every night would leave gaps in the Energy dashboard, so this
    one holds its last value instead.
    """

    entity_description: KacoSensorDescription

    def __init__(self, coordinator: KacoCoordinator, description: KacoSensorDescription) -> None:
        """Set up the lifetime energy total."""
        super().__init__(coordinator, description, description.sub_system)

    @property
    def available(self) -> bool:
        """Always available, so the statistic survives the nightly outage."""
        return True

    async def async_added_to_hass(self) -> None:
        """Restore the last known total before the first poll lands."""
        await super().async_added_to_hass()
        if (last := await self.async_get_last_sensor_data()) is not None:
            self._attr_native_value = last.native_value
        self._process_data()

    def _handle_coordinator_update(self) -> None:
        self._process_data()
        super()._handle_coordinator_update()

    def _process_data(self) -> None:
        """Take the new total, unless it would be a step backwards."""
        value = self.entity_description.value_fn(self.coordinator.device)
        if value is None:
            return
        last = self._attr_native_value
        if (
            isinstance(last, (int, float))
            and isinstance(value, (int, float))
            and last * 0.99 <= value < last
        ):
            # A small decrease is a firmware glitch, not lost generation.
            # Accepting it would make TOTAL_INCREASING infer a meter reset.
            return
        self._attr_native_value = value
