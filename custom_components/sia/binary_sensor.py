import logging
import json

DOMAIN = 'sia'
_LOGGER = logging.getLogger(__name__)

def setup_platform(hass, config, add_entities, discovery_info=None):
    devices = []
    for account in hass.data[DOMAIN]:
        for device in hass.data[DOMAIN][account]._states:
            devices.append(hass.data[DOMAIN][account]._states[device])  
    add_entities(devices)

