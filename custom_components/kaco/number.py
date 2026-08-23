"""Setpoints written to the inverter's immediate controls."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from homeassistant.components.number import (
    NumberDeviceClass,
    NumberEntity,
    NumberEntityDescription,
    NumberMode,
)
from homeassistant.const import PERCENTAGE, EntityCategory
from homeassistant.exceptions import HomeAssistantError
from modbus_connection import ModbusError

from .const import DOMAIN
from .entity import KacoEntity

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
    from kaco_modbus import KacoInverter

    from . import KacoConfigEntry
    from .coordinator import KacoCoordinator


@dataclass(frozen=True, kw_only=True)
class KacoNumberDescription(NumberEntityDescription):
    """A setpoint, with how to read it and how to write it."""

    value_fn: Callable[[KacoInverter], float | None]
    set_fn: Callable[[KacoInverter, float], Awaitable[None]]


NUMBERS: tuple[KacoNumberDescription, ...] = (
    KacoNumberDescription(
        key="power_limit_setpoint",
        translation_key="power_limit_setpoint",
        native_unit_of_measurement=PERCENTAGE,
        native_min_value=0,
        native_max_value=100,
        native_step=1,
        mode=NumberMode.SLIDER,
        entity_category=EntityCategory.CONFIG,
        entity_registry_enabled_default=False,
        value_fn=lambda device: getattr(device.controls, "w_max_lim_pct", None),
        set_fn=lambda device, value: device.async_set_power_limit(value),
    ),
    KacoNumberDescription(
        key="power_factor_setpoint",
        translation_key="power_factor_setpoint",
        device_class=NumberDeviceClass.POWER_FACTOR,
        native_min_value=-1,
        native_max_value=1,
        native_step=0.01,
        mode=NumberMode.BOX,
        entity_category=EntityCategory.CONFIG,
        entity_registry_enabled_default=False,
        value_fn=lambda device: getattr(device.controls, "out_pf_set", None),
        set_fn=lambda device, value: device.async_set_power_factor(value),
    ),
    KacoNumberDescription(
        key="reactive_power_setpoint",
        translation_key="reactive_power_setpoint",
        native_unit_of_measurement=PERCENTAGE,
        native_min_value=-100,
        native_max_value=100,
        native_step=1,
        mode=NumberMode.BOX,
        entity_category=EntityCategory.CONFIG,
        entity_registry_enabled_default=False,
        value_fn=lambda device: getattr(device.controls, "v_ar_w_max_pct", None),
        set_fn=lambda device, value: device.async_set_reactive_power(value),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: KacoConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the setpoints, if this inverter can be controlled at all."""
    data = entry.runtime_data
    if data.device.controls is None:
        return
    async_add_entities(KacoNumber(data.settings, description) for description in NUMBERS)


class KacoNumber(KacoEntity, NumberEntity):
    """A writable setpoint on SunSpec model 123."""

    entity_description: KacoNumberDescription

    def __init__(
        self, coordinator: KacoCoordinator, description: KacoNumberDescription
    ) -> None:
        """Set up a setpoint backed by the controls component."""
        super().__init__(coordinator, description, "controls")

    @property
    def native_value(self) -> float | None:
        """The setpoint currently held by the inverter."""
        return self.entity_description.value_fn(self.coordinator.device)

    async def async_set_native_value(self, value: float) -> None:
        """Write a new setpoint."""
        try:
            await self.entity_description.set_fn(self.coordinator.device, value)
        except ModbusError as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="write_failed",
                translation_placeholders={"error": str(err)},
            ) from err
        # The library re-read the controls component as part of the write, so
        # this entity is already current. Write it now rather than waiting for
        # the coordinator: async_request_refresh is debounced, so a second
        # change inside the cooldown would appear to do nothing.
        self.async_write_ha_state()
        await self.coordinator.async_request_refresh()
