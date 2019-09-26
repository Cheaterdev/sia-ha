"""Module for SIA Alarm Control Panels."""

import logging

from homeassistant.core import callback
from homeassistant.helpers.entity import generate_entity_id
from homeassistant.helpers.event import async_track_point_in_utc_time
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.util.dt import utcnow

from . import (
    ALARM_FORMAT,
    CONF_PING_INTERVAL,
    CONF_ZONE,
    PING_INTERVAL_MARGIN,
    STATE_ALARM_ARMED_AWAY,
    STATE_ALARM_ARMED_CUSTOM_BYPASS,
    STATE_ALARM_ARMED_NIGHT,
    STATE_ALARM_DISARMED,
    STATE_ALARM_TRIGGERED,
)

DOMAIN = "sia"
_LOGGER = logging.getLogger(__name__)


def setup_platform(hass, config, add_entities, discovery_info=None):
    """Implementation of platform setup from HA."""
    devices = []
    for account in hass.data[DOMAIN]:
        for device in hass.data[DOMAIN][account]._states:
            new_device = hass.data[DOMAIN][account]._states[device]
            if isinstance(new_device, SIAAlarmControlPanel):
                devices.append(new_device)

    add_entities(devices)


class SIAAlarmControlPanel(RestoreEntity):
    """Class for SIA Alarm Control Panels."""

    def __init__(self, entity_id, name, device_class, zone, ping_interval, hass):
        self._should_poll = False
        self._entity_id = generate_entity_id(
            entity_id_format=ALARM_FORMAT, name=entity_id, hass=hass
        )
        self._name = name
        self.hass = hass
        self._ping_interval = ping_interval
        self._attr = {CONF_PING_INTERVAL: self.ping_interval, CONF_ZONE: zone}
        self._is_available = True
        self._remove_unavailability_tracker = None
        self._state = None

    async def async_added_to_hass(self):
        """Once the panel is added, see if it was there before and pull in that state."""
        await super().async_added_to_hass()
        state = await self.async_get_last_state()
        if state is not None and state.state is not None:
            if state.state == STATE_ALARM_ARMED_AWAY:
                self._state = STATE_ALARM_ARMED_AWAY
            elif state.state == STATE_ALARM_ARMED_NIGHT:
                self._state = STATE_ALARM_ARMED_NIGHT
            elif state.state == STATE_ALARM_TRIGGERED:
                self._state = STATE_ALARM_TRIGGERED
            elif state.state == STATE_ALARM_DISARMED:
                self._state = STATE_ALARM_DISARMED
            elif state.state == STATE_ALARM_ARMED_CUSTOM_BYPASS:
                self._state = STATE_ALARM_ARMED_CUSTOM_BYPASS
            else:
                self._state = None
        else:
            self._state = STATE_ALARM_DISARMED  # assume disarmed
        self._async_track_unavailable()

    @property
    def entity_id(self):
        """Get entity_id."""
        return self._entity_id

    @property
    def name(self):
        """Get Name."""
        return self._name

    @property
    def ping_interval(self):
        """Get ping_interval."""
        return str(self._ping_interval)

    @property
    def state(self):
        """Get state."""
        return self._state

    @property
    def unique_id(self) -> str:
        """Get unique_id."""
        return self._name

    @property
    def available(self):
        """Get availability."""
        return self._is_available

    def alarm_disarm(self, code=None):
        """Method for disarming, not implemented."""
        _LOGGER.debug("Not implemented.")

    def alarm_arm_home(self, code=None):
        """Method for arming, not implemented."""
        _LOGGER.debug("Not implemented.")

    def alarm_arm_away(self, code=None):
        """Method for arming, not implemented."""
        _LOGGER.debug("Not implemented.")

    def alarm_arm_night(self, code=None):
        """Method for arming, not implemented."""
        _LOGGER.debug("Not implemented.")

    def alarm_trigger(self, code=None):
        """Method for triggering, not implemented."""
        _LOGGER.debug("Not implemented.")

    def alarm_arm_custom_bypass(self, code=None):
        """Method for arming, not implemented."""
        _LOGGER.debug("Not implemented.")

    @property
    def device_state_attributes(self):
        return self._attr

    @state.setter
    def state(self, state):
        self._state = state
        self.async_schedule_update_ha_state()

    def assume_available(self):
        """Reset unavalability tracker."""
        self._async_track_unavailable()

    @callback
    def _async_track_unavailable(self):
        """Callback method for resetting unavailability."""
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
