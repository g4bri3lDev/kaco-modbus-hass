"""Constants for the KACO blueplanet custom integration."""

from datetime import timedelta

DOMAIN = "kaco"
MODBUS_CONNECTION_DOMAIN = "modbus_connection"
CONF_CONNECTION_ENTRY_ID = "connection_entry_id"
CONF_UNIT_ID = "unit_id"
DEFAULT_UNIT_ID = 1
SCAN_INTERVAL = timedelta(seconds=10)
