"""Diagnostics, including a register snapshot that replays into tests."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import CONF_HOST

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant

    from . import KacoConfigEntry

TO_REDACT = {CONF_HOST, "serial_number"}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: KacoConfigEntry
) -> dict[str, Any]:
    """Return everything useful about this inverter.

    The raw register map is included because it can be loaded straight into
    ``modbus_connection.mock`` to reproduce a reported problem without the
    hardware. The serial number is redacted, so the registers holding it are
    dropped too rather than leaking it back.
    """
    data = entry.runtime_data
    device = data.device
    info = device.info
    assert info is not None

    registers = await device.async_read_raw()

    # Model 1 carries the serial number in the clear; strip those registers.
    if device.models is not None and (common := device.models.first(1)) is not None:
        serial_start = common.address + 50  # model 1 offset of "sn"
        for address in range(serial_start, serial_start + 16):
            registers.get("holding", {}).pop(address, None)

    return async_redact_data(
        {
            "device": {
                "manufacturer": info.manufacturer,
                "model": info.model,
                "firmware": info.firmware,
                "options": info.options,
                "serial_number": info.serial_number,
                "base_address": device.base_address,
                "models": sorted(device.models or ()),
                "strings": len(device.strings),
                "setpoints_held": device.setpoints_held,
                "revert_seconds": device.revert_seconds,
            },
            "readings": {
                "updated": data.readings.data.updated,
                "failed": {n: str(e) for n, e in data.readings.data.failed.items()},
            },
            "settings": {
                "updated": data.settings.data.updated,
                "failed": {n: str(e) for n, e in data.settings.data.failed.items()},
            },
            "entry": dict(entry.data),
            "registers": registers,
        },
        TO_REDACT,
    )
