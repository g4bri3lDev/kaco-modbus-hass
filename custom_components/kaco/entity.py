"""Base entity carrying the device registry info."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import EntityDescription
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import KacoCoordinator


class KacoEntity(CoordinatorEntity[KacoCoordinator]):
    """An entity of one KACO inverter."""

    _attr_has_entity_name = True

    def __init__(
        self, coordinator: KacoCoordinator, description: EntityDescription
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        probe = coordinator.device.probe
        serial = probe.serial or "unknown"
        self._attr_unique_id = f"{serial}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, serial)},
            manufacturer=probe.manufacturer or "KACO new energy",
            model=probe.model,
            serial_number=probe.serial,
            sw_version=probe.firmware,
        )
