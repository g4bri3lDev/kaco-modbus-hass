"""What every KACO entity shares."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.helpers.update_coordinator import CoordinatorEntity

if TYPE_CHECKING:
    from homeassistant.helpers.entity import EntityDescription

    from .coordinator import KacoCoordinator


class KacoEntity(CoordinatorEntity["KacoCoordinator"]):
    """An entity backed by one sub-system of the inverter.

    Sub-systems are polled independently, so an entity is unavailable when
    *its* component failed to read — not when any of them did.
    """

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: KacoCoordinator,
        description: EntityDescription,
        sub_system: str,
    ) -> None:
        """Bind this entity to the *sub_system* component it reads from."""
        super().__init__(coordinator)
        self.entity_description = description
        self._sub_system = sub_system

        info = coordinator.device.info
        assert info is not None
        self._attr_unique_id = f"{info.serial_number}_{description.key}"
        self._attr_device_info = coordinator.device_info

    @property
    def available(self) -> bool:
        """Whether this entity's own sub-system answered the last poll."""
        return super().available and self._sub_system in self.coordinator.data.updated
