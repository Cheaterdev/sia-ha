"""Module for SIA Sensors."""

import logging

from homeassistant.components.sensor import ENTITY_ID_FORMAT as SENSOR_FORMAT

from homeassistant.helpers.entity import Entity, generate_entity_id
from homeassistant.util.dt import utcnow

from . import CONF_ZONE, CONF_PING_INTERVAL

DOMAIN = "sia"
_LOGGER = logging.getLogger(__name__)


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Implementation of platform setup from HA."""
    devices = [
        device
        for hub in hass.data[DOMAIN].values()
        for device in hub._states.values()
        if isinstance(device, SIASensor)
    ]
    _LOGGER.debug("SIASensor: setup: devices: " + str(devices))
    async_add_entities(devices)


class SIASensor(Entity):
    """Class for SIA Sensors."""

    def __init__(self, entity_id, name, device_class, zone, ping_interval, hass):
        self._should_poll = False
        self._device_class = device_class
        self._entity_id = generate_entity_id(
            entity_id_format=SENSOR_FORMAT, name=entity_id, hass=hass
        )
        self._state = utcnow()
        self._attr = {CONF_PING_INTERVAL: str(ping_interval), CONF_ZONE: zone}
        self._name = name
        self.hass = hass

    @property
    def entity_id(self):
        """Get entity_id."""
        return self._entity_id

    @property
    def name(self):
        return self._name

    @property
    def state(self):
        return self._state.isoformat()

    @property
    def device_state_attributes(self):
        return self._attr

    def add_attribute(self, attr):
        """Update attributes."""
        self._attr.update(attr)

    @property
    def device_class(self):
        return self._device_class

    @state.setter
    def state(self, state):
        self._state = state
        self.async_schedule_update_ha_state()

    def assume_available(self):
        """Stub method, to keep signature the same between all SIA components."""
        pass

    @property
    def icon(self):
        """Return the icon to use in the frontend, if any."""
        return "mdi:alarm-light-outline"
