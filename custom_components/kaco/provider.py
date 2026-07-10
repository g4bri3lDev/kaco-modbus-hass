"""Locate the shared modbus_connection provider.

Prefer the custom component (installable today); fall back to the core
integration once Home Assistant ships it in a release.
"""

try:
    from custom_components.modbus_connection import async_get_unit
except ImportError:  # pragma: no cover
    from homeassistant.components.modbus_connection import (  # type: ignore[no-redef]
        async_get_unit,
    )

__all__ = ["async_get_unit"]
