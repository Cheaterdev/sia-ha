"""Module for SIA Sensors."""

import logging
import datetime as dt

from homeassistant.core import callback
from homeassistant.components.sensor import ENTITY_ID_FORMAT as SENSOR_FORMAT
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity import Entity, generate_entity_id
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.util.dt import utcnow

from . import CONF_ZONE, CONF_PING_INTERVAL, DATA_UPDATED

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


class SIASensor(RestoreEntity):
    """Class for SIA Sensors."""

    def __init__(
        self, hub_name, entity_id, name, device_class, zone, ping_interval, hass
    ):
        self._should_poll = False
        self._device_class = device_class
        self.entity_id = generate_entity_id(
            entity_id_format=SENSOR_FORMAT, name=entity_id, hass=hass
        )
        self._unique_id = f"{hub_name}-{self.entity_id}"
        self._state = utcnow()
        self._attr = {CONF_PING_INTERVAL: str(ping_interval), CONF_ZONE: zone}
        self._name = name
        self.hass = hass

    async def async_added_to_hass(self):
        """Once the sensor is added, see if it was there before and pull in that state."""
        await super().async_added_to_hass()
        state = await self.async_get_last_state()
        if state is not None and state.state is not None:
            _LOGGER.debug("SIASensor: init: old state: " + state.state)
            self.state = dt.datetime.strptime(state.state, "%Y-%m-%dT%H:%M:%S.%f%z")
        else:
            return
        _LOGGER.debug("SIASensor: added: state: " + str(state))
        async_dispatcher_connect(
            self.hass, DATA_UPDATED, self._schedule_immediate_update
        )

    @callback
    def _schedule_immediate_update(self):
        self.async_schedule_update_ha_state(True)

    @property
    def name(self):
        return self._name

    @property
    def unique_id(self) -> str:
        """Get unique_id."""
        return self._unique_id

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
