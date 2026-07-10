"""Fixtures: a stub modbus_connection provider over a seeded mock unit."""

from __future__ import annotations

import sys
from pathlib import Path
from types import ModuleType

import pytest
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from modbus_connection.mock import MockModbusConnection, MockModbusUnit
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    MockModule,
    mock_integration,
    mock_platform,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

_OUR_COMPONENTS_DIR = str(REPO_ROOT / "custom_components")


def _ensure_our_custom_components_are_discoverable() -> None:
    """Make `custom_components.kaco` resolve regardless of import order.

    pytest-homeassistant-custom-component ships its own regular
    `custom_components` package (with an `__init__.py`) under its
    `testing_config` directory, and the `hass` fixture prepends that
    directory to `sys.path` ahead of everything else -- including the repo
    root this conftest inserts. Because `custom_components` is a *regular*
    package (has `__init__.py`) rather than a namespace package, that
    testing_config copy "wins" the top-level import outright and our
    sibling `custom_components/kaco` directory is never discovered.

    Once `custom_components` has actually been imported (i.e. once the
    `hass` fixture has done its `sys.path` dance), extend its search path
    with our directory so submodule imports (e.g. `custom_components.kaco`)
    find ours too. Called from the `auto_enable_custom_integrations`
    fixture, which depends on `hass` and therefore always runs after that
    import has happened.
    """
    cc_pkg = sys.modules.get("custom_components")
    if cc_pkg is not None and _OUR_COMPONENTS_DIR not in cc_pkg.__path__:
        cc_pkg.__path__.append(_OUR_COMPONENTS_DIR)


MODBUS_CONNECTION_DOMAIN = "modbus_connection"
_PROVIDER_UNITS = "test_modbus_connection_units"
CONNECTION_ENTRY_ID = "test-connection-entry"
UNIT_ID = 1


def _async_get_unit(
    hass: HomeAssistant, connection_entry_id: str, unit_id: int
) -> MockModbusUnit:
    units = hass.data.get(_PROVIDER_UNITS, {})
    try:
        return units[(connection_entry_id, unit_id)]
    except KeyError as err:
        raise ConfigEntryNotReady("test Modbus connection not ready") from err


# The real modbus_connection provider integration is installed separately in
# Home Assistant. Only this repository is checked out during tests, so stub
# the small public provider boundary that custom_components.kaco.provider
# consumes.
_provider = ModuleType("custom_components.modbus_connection")
_provider.async_get_unit = _async_get_unit
sys.modules["custom_components.modbus_connection"] = _provider


async def _async_setup_modbus_connection_entry(
    _hass: HomeAssistant, _entry: ConfigEntry
) -> bool:
    """Set up the simulated Modbus Connection provider entry."""
    return True


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(hass: HomeAssistant, enable_custom_integrations):
    _ensure_our_custom_components_are_discoverable()

    # `kaco`'s manifest declares `modbus_connection` as a dependency, so
    # Home Assistant insists on being able to set that domain up before it
    # will hand out the `kaco` config flow. Register a stand-in integration
    # for it -- the sys.modules stub above supplies async_get_unit to the
    # kaco code, while this loader mock satisfies the manifest dependency.
    mock_integration(
        hass,
        MockModule(
            MODBUS_CONNECTION_DOMAIN,
            async_setup_entry=_async_setup_modbus_connection_entry,
        ),
        built_in=False,
    )
    mock_platform(hass, f"{MODBUS_CONNECTION_DOMAIN}.config_flow", None)

    # A selectable Modbus Connection entry for the kaco config flow to list.
    connection_entry = MockConfigEntry(
        domain=MODBUS_CONNECTION_DOMAIN,
        entry_id=CONNECTION_ENTRY_ID,
        title="Test connection",
    )
    connection_entry.add_to_hass(hass)

    yield


@pytest.fixture
def mock_unit(hass: HomeAssistant) -> MockModbusUnit:
    from kaco_modbus.testing import BLUEPLANET_86TL3_REGISTERS

    connection = MockModbusConnection()
    unit = connection.for_unit(UNIT_ID)
    for address, value in BLUEPLANET_86TL3_REGISTERS.items():
        unit.holding[address] = value
    hass.data.setdefault(_PROVIDER_UNITS, {})[(CONNECTION_ENTRY_ID, UNIT_ID)] = unit
    return unit


@pytest.fixture
def config_entry(hass: HomeAssistant) -> MockConfigEntry:
    entry = MockConfigEntry(
        domain="kaco",
        title="KACO new energy blueplanet 8.6 TL3",
        unique_id="8.6TL01723456",
        data={"connection_entry_id": CONNECTION_ENTRY_ID, "unit_id": UNIT_ID},
    )
    entry.add_to_hass(hass)
    return entry
