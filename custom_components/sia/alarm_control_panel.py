import logging
import json

from . import SIAAlarmControlPanel

DOMAIN = "sia"
_LOGGER = logging.getLogger(__name__)


def setup_platform(hass, config, add_entities, discovery_info=None):
    devices = []
    for account in hass.data[DOMAIN]:
        for device in hass.data[DOMAIN][account]._states:
            new_device = hass.data[DOMAIN][account]._states[device]
            if isinstance(new_device, SIAAlarmControlPanel):
                devices.append(new_device)

    add_entities(devices)
