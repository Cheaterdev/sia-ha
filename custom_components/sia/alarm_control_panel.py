"""Module for SIA Alarm Control Panels."""

import logging

from homeassistant.components.alarm_control_panel import (
    ENTITY_ID_FORMAT as ALARM_FORMAT,
    AlarmControlPanelEntity,
)
from homeassistant.const import (
    CONF_ZONE,
    STATE_ALARM_ARMED_AWAY,
    STATE_ALARM_ARMED_CUSTOM_BYPASS,
    STATE_ALARM_ARMED_NIGHT,
    STATE_ALARM_DISARMED,
    STATE_ALARM_TRIGGERED,
)
from homeassistant.core import callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.event import async_track_point_in_utc_time
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.util.dt import utcnow

from .const import (
    CONF_ACCOUNT,
    CONF_PING_INTERVAL,
    DATA_UPDATED,
    DOMAIN,
    PING_INTERVAL_MARGIN,
    PREVIOUS_STATE,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_devices):
    """Set up sia_alarm_control_panel from a config entry."""
    async_add_devices(
        [
            device
            for device in hass.data[DOMAIN][entry.entry_id].states.values()
            if isinstance(device, SIAAlarmControlPanel)
        ]
    )

    return True


class SIAAlarmControlPanel(AlarmControlPanelEntity, RestoreEntity):
    """Class for SIA Alarm Control Panels."""

    def __init__(self, entity_id, name, port, account, zone, ping_interval, hass):
        """Create SIAAlarmControlPanel object."""
        self.entity_id = ALARM_FORMAT.format(entity_id)
        self._unique_id = entity_id
        self._name = name
        self._port = port
        self._account = account
        self._zone = zone
        self._ping_interval = ping_interval
        self.hass = hass

        self._should_poll = False
        self._is_available = True
        self._remove_unavailability_tracker = None
        self._state = None
        self._old_state = None
        self._attr = {
            CONF_ACCOUNT: self._account,
            CONF_PING_INTERVAL: str(self._ping_interval),
            CONF_ZONE: self._zone,
        }

    async def async_added_to_hass(self):
        """Once the panel is added, see if it was there before and pull in that state."""
        await super().async_added_to_hass()
        state = await self.async_get_last_state()
        if state is not None and state.state is not None:
            if state.state == STATE_ALARM_ARMED_AWAY:
                self.state = STATE_ALARM_ARMED_AWAY
            elif state.state == STATE_ALARM_ARMED_NIGHT:
                self.state = STATE_ALARM_ARMED_NIGHT
            elif state.state == STATE_ALARM_TRIGGERED:
                self.state = STATE_ALARM_TRIGGERED
            elif state.state == STATE_ALARM_DISARMED:
                self.state = STATE_ALARM_DISARMED
            elif state.state == STATE_ALARM_ARMED_CUSTOM_BYPASS:
                self.state = STATE_ALARM_ARMED_CUSTOM_BYPASS
            else:
                self.state = None
        else:
            self.state = None
        await self._async_track_unavailable()
        async_dispatcher_connect(
            self.hass, DATA_UPDATED, self._schedule_immediate_update
        )

    @callback
    def _schedule_immediate_update(self):
        self.async_schedule_update_ha_state(True)

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
    def account(self):
        """Return device account."""
        return self._account

    @property
    def unique_id(self) -> str:
        """Get unique_id."""
        return self._unique_id

    @property
    def available(self):
        """Get availability."""
        return self._is_available

    @property
    def device_state_attributes(self):
        """Return device attributes."""
        return self._attr

    @state.setter
    def state(self, state):
        """Set state."""
        temp = self._old_state if state == PREVIOUS_STATE else state
        self._old_state = self._state
        self._state = temp
        self.async_schedule_update_ha_state()

    async def assume_available(self):
        """Reset unavalability tracker."""
        await self._async_track_unavailable()

    @callback
    async def _async_track_unavailable(self):
        """Reset unavailability."""
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
        """Set availability."""
        self._remove_unavailability_tracker = None
        self._is_available = False
        self.async_schedule_update_ha_state()

    @property
    def supported_features(self) -> int:
        """Return the list of supported features."""
        return None

    @property
    def device_info(self):
        """Return the device_info."""
        return {
            "identifiers": {(DOMAIN, self.unique_id)},
            "name": self.name,
            "via_device": (DOMAIN, self._port, self._account),
        }
