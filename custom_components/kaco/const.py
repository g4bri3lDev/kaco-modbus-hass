"""Constants for the KACO integration."""

from __future__ import annotations

from datetime import timedelta
from typing import Final

DOMAIN: Final = "kaco"

CONF_UNIT_ID: Final = "unit_id"
DEFAULT_PORT: Final = 502
# Most KACO inverters are TCP-native and ignore the unit ID entirely, but one
# reached through an RS485-to-TCP gateway will not, so it stays configurable.
DEFAULT_UNIT_ID: Final = 1

# What the inverter measures changes constantly; what it is configured to do
# changes almost never. Home Assistant core does not let a user tune these.
READINGS_INTERVAL: Final = timedelta(seconds=30)
SETTINGS_INTERVAL: Final = timedelta(minutes=5)

# An inverter that is dark but still answering TCP will time out every read.
# After this many consecutive timeouts the link is dropped so the next poll
# opens a fresh one.
TIMEOUTS_BEFORE_DISCONNECT: Final = 3
