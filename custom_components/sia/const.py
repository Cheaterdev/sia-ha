"""Constants for the sia integration."""

from datetime import timedelta

from homeassistant.components.alarm_control_panel import (
    DOMAIN as ALARM_CONTROL_PANEL_DOMAIN,
)
from homeassistant.components.binary_sensor import (
    DEVICE_CLASS_MOISTURE,
    DEVICE_CLASS_SMOKE,
    DOMAIN as BINARY_SENSOR_DOMAIN,
)
from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN
from homeassistant.const import (
    DEVICE_CLASS_TIMESTAMP,
    STATE_ALARM_ARMED_AWAY,
    STATE_ALARM_ARMED_CUSTOM_BYPASS,
    STATE_ALARM_ARMED_NIGHT,
    STATE_ALARM_DISARMED,
    STATE_ALARM_TRIGGERED,
)

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
PREVIOUS_STATE = "PREVIOUS_STATE"
UTCNOW = "utcnow"
LAST_MESSAGE = "lastmessage"

PLATFORMS = [SENSOR_DOMAIN, BINARY_SENSOR_DOMAIN, ALARM_CONTROL_PANEL_DOMAIN]

REACTIONS = {
    "BA": {"type": DEVICE_CLASS_ALARM, "new_state": STATE_ALARM_TRIGGERED},
    "BR": {"type": DEVICE_CLASS_ALARM, "new_state": PREVIOUS_STATE},
    "CA": {"type": DEVICE_CLASS_ALARM, "new_state": STATE_ALARM_ARMED_AWAY},
    "CF": {"type": DEVICE_CLASS_ALARM, "new_state": STATE_ALARM_ARMED_CUSTOM_BYPASS},
    "CG": {"type": DEVICE_CLASS_ALARM, "new_state": STATE_ALARM_ARMED_AWAY},
    "CL": {"type": DEVICE_CLASS_ALARM, "new_state": STATE_ALARM_ARMED_AWAY},
    "CP": {"type": DEVICE_CLASS_ALARM, "new_state": STATE_ALARM_ARMED_AWAY},
    "CQ": {"type": DEVICE_CLASS_ALARM, "new_state": STATE_ALARM_ARMED_AWAY},
    "GA": {"type": DEVICE_CLASS_SMOKE, "new_state": True},
    "GH": {"type": DEVICE_CLASS_SMOKE, "new_state": False},
    "NL": {"type": DEVICE_CLASS_ALARM, "new_state": STATE_ALARM_ARMED_NIGHT},
    "OA": {"type": DEVICE_CLASS_ALARM, "new_state": STATE_ALARM_DISARMED},
    "OG": {"type": DEVICE_CLASS_ALARM, "new_state": STATE_ALARM_DISARMED},
    "OP": {"type": DEVICE_CLASS_ALARM, "new_state": STATE_ALARM_DISARMED},
    "OQ": {"type": DEVICE_CLASS_ALARM, "new_state": STATE_ALARM_DISARMED},
    "OR": {"type": DEVICE_CLASS_ALARM, "new_state": STATE_ALARM_DISARMED},
    "RP": {"type": DEVICE_CLASS_TIMESTAMP, "new_state_eval": UTCNOW},
    "TA": {"type": DEVICE_CLASS_ALARM, "new_state": STATE_ALARM_TRIGGERED},
    "WA": {"type": DEVICE_CLASS_MOISTURE, "new_state": True},
    "WH": {"type": DEVICE_CLASS_MOISTURE, "new_state": False},
    "YG": {"type": DEVICE_CLASS_TIMESTAMP, "attr": LAST_MESSAGE},
}
