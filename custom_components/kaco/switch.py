"""Turning the inverter's control modes on and off."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from homeassistant.components.switch import (
    SwitchDeviceClass,
    SwitchEntity,
    SwitchEntityDescription,
)
from homeassistant.const import EntityCategory
from homeassistant.exceptions import HomeAssistantError
from kaco_modbus import Conn, OutPFSetEna, VArPctEna, WMaxLimEna
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
class KacoSwitchDescription(SwitchEntityDescription):
    """A control mode, with how to read it and how to set it."""

    is_on_fn: Callable[[KacoInverter], bool | None]
    set_fn: Callable[[KacoInverter, bool], Awaitable[None]]


SWITCHES: tuple[KacoSwitchDescription, ...] = (
    KacoSwitchDescription(
        key="power_limit",
        translation_key="power_limit",
        entity_category=EntityCategory.CONFIG,
        entity_registry_enabled_default=False,
        is_on_fn=lambda device: (
            getattr(device.controls, "w_max_lim_ena", None) is WMaxLimEna.ENABLED
        ),
        set_fn=lambda device, on: (
            # Re-applying the setpoint the inverter already holds, so enabling
            # never resurrects a stale limit from an earlier session.
            device.async_set_power_limit(getattr(device.controls, "w_max_lim_pct", None) or 100.0)
            if on
            else device.async_clear_power_limit()
        ),
    ),
    KacoSwitchDescription(
        key="fixed_power_factor",
        translation_key="fixed_power_factor",
        entity_category=EntityCategory.CONFIG,
        entity_registry_enabled_default=False,
        is_on_fn=lambda device: (
            getattr(device.controls, "out_pf_set_ena", None) is OutPFSetEna.ENABLED
        ),
        set_fn=lambda device, on: (
            device.async_set_power_factor(getattr(device.controls, "out_pf_set", None) or 1.0)
            if on
            else device.async_clear_power_factor()
        ),
    ),
    KacoSwitchDescription(
        key="reactive_power",
        translation_key="reactive_power",
        entity_category=EntityCategory.CONFIG,
        entity_registry_enabled_default=False,
        is_on_fn=lambda device: (
            getattr(device.controls, "v_ar_pct_ena", None) is VArPctEna.ENABLED
        ),
        set_fn=lambda device, on: (
            device.async_set_reactive_power(getattr(device.controls, "v_ar_w_max_pct", None) or 0.0)
            if on
            else device.async_clear_reactive_power()
        ),
    ),
    # Disconnecting stops export entirely, so this is a switch of last resort.
    KacoSwitchDescription(
        key="grid_connection",
        translation_key="grid_connection",
        device_class=SwitchDeviceClass.SWITCH,
        entity_category=EntityCategory.CONFIG,
        entity_registry_enabled_default=False,
        is_on_fn=lambda device: getattr(device.controls, "conn", None) is Conn.CONNECT,
        set_fn=lambda device, on: device.async_set_connected(on),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: KacoConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the control switches, if this inverter has model 123."""
    data = entry.runtime_data
    if data.device.controls is None:
        return
    async_add_entities(KacoSwitch(data.settings, description) for description in SWITCHES)


class KacoSwitch(KacoEntity, SwitchEntity):
    """One control mode of SunSpec model 123."""

    entity_description: KacoSwitchDescription

    def __init__(
        self, coordinator: KacoCoordinator, description: KacoSwitchDescription
    ) -> None:
        """Set up a switch backed by the controls component."""
        super().__init__(coordinator, description, "controls")

    @property
    def is_on(self) -> bool | None:
        """Whether this control mode is currently enabled."""
        return self.entity_description.is_on_fn(self.coordinator.device)

    async def async_turn_on(self, **kwargs: object) -> None:
        """Enable this control mode."""
        await self._async_set(True)

    async def async_turn_off(self, **kwargs: object) -> None:
        """Disable this control mode."""
        await self._async_set(False)

    async def _async_set(self, on: bool) -> None:
        try:
            await self.entity_description.set_fn(self.coordinator.device, on)
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
