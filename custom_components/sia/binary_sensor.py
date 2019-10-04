"""Module for SIA Binary Sensors."""

import logging

from homeassistant.core import callback
from homeassistant.helpers.entity import generate_entity_id
from homeassistant.helpers.event import async_track_point_in_utc_time
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.util.dt import utcnow

from . import (
    CONF_PING_INTERVAL,
    PING_INTERVAL_MARGIN,
    CONF_ZONE,
    BINARY_SENSOR_FORMAT,
    STATE_ON,
    STATE_OFF,
)

DOMAIN = "sia"
_LOGGER = logging.getLogger(__name__)


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Implementation of platform setup from HA."""
    devices = [
        device
        for hub in hass.data[DOMAIN].values()
        for device in hub._states.values()
        if isinstance(device, SIABinarySensor)
    ]
    _LOGGER.debug("SIABinarySensor: setup: devices: " + str(devices))
    async_add_entities(devices)


class SIABinarySensor(RestoreEntity):
    """Class for SIA Binary Sensors."""

    def __init__(self, entity_id, name, device_class, zone, ping_interval, hass):
        self._device_class = device_class
        self._should_poll = False
        self._ping_interval = ping_interval
        self._attr = {CONF_PING_INTERVAL: self.ping_interval, CONF_ZONE: zone}
        self._entity_id = generate_entity_id(
            entity_id_format=BINARY_SENSOR_FORMAT, name=entity_id, hass=hass
        )
        self._name = name
        self.hass = hass
        self._is_available = True
        self._remove_unavailability_tracker = None
        self._state = None

    @property
    def entity_id(self):
        """Get entity_id."""
        return self._entity_id

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        state = await self.async_get_last_state()
        if state is not None and state.state is not None:
            self.state = state.state == STATE_ON
        else:
            self.state = None
        _LOGGER.debug("SIABinarySensor: added: state: " + str(state))
        self._async_track_unavailable()

    @property
    def name(self):
        return self._name

    @property
    def ping_interval(self):
        """Get ping_interval."""
        return str(self._ping_interval)

    @property
    def state(self):
        return STATE_ON if self.is_on else STATE_OFF

    @property
    def unique_id(self) -> str:
        return self._name

    @property
    def available(self):
        return self._is_available

    @property
    def device_state_attributes(self):
        return self._attr

    @property
    def device_class(self):
        return self._device_class

    @property
    def is_on(self):
        """Get whether the sensor is set to ON."""
        return self._state

    @state.setter
    def state(self, state):
        self._state = state
        self.async_schedule_update_ha_state()

    def assume_available(self):
        """Reset unavalability tracker."""
        self._async_track_unavailable()

    @callback
    def _async_track_unavailable(self):
        if self._remove_unavailability_tracker:
            self._remove_unavailability_tracker()
        self._remove_unavailability_tracker = async_track_point_in_utc_time(
            self.hass,
            self._async_set_unavailable,
            utcnow() + self._ping_interval + PING_INTERVAL_MARGIN,
        )
        if not self._is_available:
            self._is_available = True
            return True
        return False

    @callback
    def _async_set_unavailable(self, now):
        self._remove_unavailability_tracker = None
        self._is_available = False
        self.async_schedule_update_ha_state()
