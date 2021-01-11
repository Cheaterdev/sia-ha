"""Constants for the sia integration."""

from datetime import timedelta

from homeassistant.components.alarm_control_panel import (
    DOMAIN as ALARM_CONTROL_PANEL_DOMAIN,
)
from homeassistant.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN
from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN

CONF_ACCOUNT = "account"
CONF_ACCOUNTS = "accounts"
CONF_ADDITIONAL_ACCOUNTS = "additional_account"
CONF_PING_INTERVAL = "ping_interval"
CONF_ENCRYPTION_KEY = "encryption_key"
CONF_ZONES = "zones"
DOMAIN = "sia"
DATA_UPDATED = f"{DOMAIN}_data_updated"
DEFAULT_NAME = "SIA Alarm"
DEVICE_CLASS_ALARM = "alarm"
HUB_SENSOR_NAME = "last_heartbeat"
HUB_ZONE = 0
PING_INTERVAL_MARGIN = timedelta(seconds=30)
PREVIOUS_STATE = "previous_state"
UTCNOW = "utcnow"
LAST_MESSAGE = "last_message"

PLATFORMS = [SENSOR_DOMAIN, BINARY_SENSOR_DOMAIN, ALARM_CONTROL_PANEL_DOMAIN]

REACTIONS = {
    "AT": {"type": "timestamp", "attr": "last_message"},
    "AR": {"type": "timestamp", "attr": "last_message"},
    "BA": {"type": "alarm", "new_state": "triggered"},
    "PA": {"type": "alarm", "new_state": "triggered"},
    "JA": {"type": "alarm", "new_state": "triggered"},
    "BR": {"type": "alarm", "new_state": "previous_state"},
    "CA": {"type": "alarm", "new_state": "armed_away"},
    "CF": {"type": "alarm", "new_state": "armed_custom_bypass"},
    "CG": {"type": "alarm", "new_state": "armed_away"},
    "CL": {"type": "alarm", "new_state": "armed_away"},
    "CP": {"type": "alarm", "new_state": "armed_away"},
    "CQ": {"type": "alarm", "new_state": "armed_away"},
    "CS": {"type": "alarm", "new_state": "armed_away"},
    "GA": {"type": "smoke", "new_state": True},
    "GH": {"type": "smoke", "new_state": False},
    "FA": {"type": "smoke", "new_state": True},
    "FH": {"type": "smoke", "new_state": False},
    "KA": {"type": "smoke", "new_state": True},
    "KH": {"type": "smoke", "new_state": False},
    "NC": {"type": "alarm", "new_state": "armed_night"},
    "NL": {"type": "alarm", "new_state": "armed_night"},
    "NP": {"type": "alarm", "new_state": "previous_state"},
    "NO": {"type": "alarm", "new_state": "previous_state"},
    "OA": {"type": "alarm", "new_state": "disarmed"},
    "OG": {"type": "alarm", "new_state": "disarmed"},
    "OP": {"type": "alarm", "new_state": "disarmed"},
    "OQ": {"type": "alarm", "new_state": "disarmed"},
    "OR": {"type": "alarm", "new_state": "disarmed"},
    "OS": {"type": "alarm", "new_state": "disarmed"},
    "RP": {"type": "timestamp", "new_state_eval": "utcnow"},
    "TA": {"type": "alarm", "new_state": "triggered"},
    "WA": {"type": "moisture", "new_state": True},
    "WH": {"type": "moisture", "new_state": False},
    "YG": {"type": "timestamp", "attr": "last_message"},
    "YC": {"type": "timestamp", "attr": "last_message"},
    "XI": {"type": "timestamp", "attr": "last_message"},
    "YM": {"type": "timestamp", "attr": "last_message"},
    "YA": {"type": "timestamp", "attr": "last_message"},
    "YS": {"type": "timestamp", "attr": "last_message"},
    "XQ": {"type": "timestamp", "attr": "last_message"},
    "XH": {"type": "timestamp", "attr": "last_message"},
    "YT": {"type": "timestamp", "attr": "last_message"},
    "YR": {"type": "timestamp", "attr": "last_message"},
    "TR": {"type": "timestamp", "attr": "last_message"},
    "ZZ": {"type": "timestamp", "attr": "last_message"},
    "ZY": {"type": "timestamp", "attr": "last_message"},
}

