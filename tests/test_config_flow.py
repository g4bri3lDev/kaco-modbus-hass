"""Config flow tests."""

from unittest.mock import patch

from homeassistant.config_entries import SOURCE_USER
from homeassistant.data_entry_flow import FlowResultType

from .conftest import CONNECTION_ENTRY_ID, UNIT_ID


async def test_user_flow_creates_entry(hass, mock_unit):
    result = await hass.config_entries.flow.async_init(
        "kaco", context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM

    with patch(
        "custom_components.kaco.config_flow._connection_options",
        return_value={CONNECTION_ENTRY_ID: "Test connection"},
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"connection_entry_id": CONNECTION_ENTRY_ID, "unit_id": UNIT_ID},
        )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "KACO new energy blueplanet 8.6 TL3"
    assert result["result"].unique_id == "8.6TL01723456"


async def test_user_flow_cannot_connect(hass):
    # no mock_unit fixture -> provider raises ConfigEntryNotReady
    result = await hass.config_entries.flow.async_init(
        "kaco", context={"source": SOURCE_USER}
    )
    with patch(
        "custom_components.kaco.config_flow._connection_options",
        return_value={CONNECTION_ENTRY_ID: "Test connection"},
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"connection_entry_id": CONNECTION_ENTRY_ID, "unit_id": UNIT_ID},
        )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}
