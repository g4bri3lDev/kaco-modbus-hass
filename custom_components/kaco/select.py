"""How the reactive power setpoint is interpreted."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.const import EntityCategory
from homeassistant.exceptions import HomeAssistantError
from kaco_modbus import VArPctMod
from modbus_connection import ModbusError

from .const import DOMAIN
from .entity import KacoEntity

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

    from . import KacoConfigEntry
    from .coordinator import KacoCoordinator

# The SunSpec mode enum, as option strings Home Assistant can translate.
MODES: dict[str, VArPctMod] = {mode.name.lower(): mode for mode in VArPctMod}

DESCRIPTION = SelectEntityDescription(
    key="reactive_power_mode",
    translation_key="reactive_power_mode",
    options=list(MODES),
    entity_category=EntityCategory.CONFIG,
    entity_registry_enabled_default=False,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: KacoConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the reactive power mode, if this inverter has model 123."""
    data = entry.runtime_data
    if data.device.controls is None:
        return
    async_add_entities([KacoReactivePowerMode(data.settings, DESCRIPTION)])


class KacoReactivePowerMode(KacoEntity, SelectEntity):
    """Whether a reactive power setpoint is a percentage of WMax or VArMax."""

    def __init__(self, coordinator: KacoCoordinator, description: SelectEntityDescription) -> None:
        """Set up the mode selector backed by the controls component."""
        super().__init__(coordinator, description, "controls")

    @property
    def current_option(self) -> str | None:
        """The mode the inverter is in, if it reports one we know."""
        mode = getattr(self.coordinator.device.controls, "v_ar_pct_mod", None)
        return mode.name.lower() if mode is not None else None

    async def async_select_option(self, option: str) -> None:
        """Switch mode, re-applying the setpoint so it keeps its meaning.

        The stored number means a different thing in each mode, so writing the
        mode alone would silently change what the inverter is being asked for.
        """
        device = self.coordinator.device
        assert device.controls is not None
        current = device.controls.v_ar_w_max_pct or 0.0
        try:
            await device.async_set_reactive_power(current, mode=MODES[option])
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
