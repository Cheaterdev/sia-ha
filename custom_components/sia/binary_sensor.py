"""Module for SIA Binary Sensors."""

import logging
from typing import Callable

from homeassistant.components.binary_sensor import (
    ENTITY_ID_FORMAT as BINARY_SENSOR_FORMAT,
    BinarySensorEntity,
    DEVICE_CLASS_MOISTURE,
    DEVICE_CLASS_POWER,
    DEVICE_CLASS_SMOKE,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PORT, CONF_ZONE, STATE_OFF, STATE_ON, STATE_UNKNOWN
from homeassistant.core import HomeAssistant, callback, Event
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.event import async_track_point_in_utc_time
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.util.dt import utcnow

from .const import (
    ATTR_LAST_CODE,
    ATTR_LAST_MESSAGE,
    ATTR_LAST_TIMESTAMP,
    CONF_ACCOUNT,
    CONF_ACCOUNTS,
    CONF_PING_INTERVAL,
    CONF_ZONES,
    DATA_UPDATED,
    EVENT_CODE,
    EVENT_ZONE,
    EVENT_MESSAGE,
    EVENT_TIMESTAMP,
    HUB_ZONE,
    SIA_EVENT,
    DOMAIN,
    PING_INTERVAL_MARGIN,
)
from .helpers import GET_ENTITY_AND_NAME, GET_PING_INTERVAL

_LOGGER = logging.getLogger(__name__)

ZONE_DEVICES = [
    DEVICE_CLASS_MOISTURE,
    DEVICE_CLASS_SMOKE,
]
CODE_CONSEQUENCES = {
    "AT": (DEVICE_CLASS_POWER, False),
    "AR": (DEVICE_CLASS_POWER, True),
    "GA": (DEVICE_CLASS_SMOKE, True),
    "GH": (DEVICE_CLASS_SMOKE, False),
    "FA": (DEVICE_CLASS_SMOKE, True),
    "FH": (DEVICE_CLASS_SMOKE, False),
    "KA": (DEVICE_CLASS_SMOKE, True),
    "KH": (DEVICE_CLASS_SMOKE, False),
    "WA": (DEVICE_CLASS_MOISTURE, True),
    "WH": (DEVICE_CLASS_MOISTURE, False),
}


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_devices: Callable[[], None]
) -> bool:
    """Set up sia_binary_sensor from a config entry."""

    devices = [
        SIABinarySensor(
            *GET_ENTITY_AND_NAME(
                entry.data[CONF_PORT], acc[CONF_ACCOUNT], zone, device_class
            ),
            entry.data[CONF_PORT],
            acc[CONF_ACCOUNT],
            zone,
            acc[CONF_PING_INTERVAL],
            device_class,
        )
        for acc in entry.data[CONF_ACCOUNTS]
        for zone in range(1, acc[CONF_ZONES] + 1)
        for device_class in ZONE_DEVICES
    ]
    devices.extend(
        [
            SIABinarySensor(
                *GET_ENTITY_AND_NAME(
                    entry.data[CONF_PORT],
                    acc[CONF_ACCOUNT],
                    HUB_ZONE,
                    DEVICE_CLASS_POWER,
                ),
                entry.data[CONF_PORT],
                acc[CONF_ACCOUNT],
                HUB_ZONE,
                acc[CONF_PING_INTERVAL],
                DEVICE_CLASS_POWER,
            )
            for acc in entry.data[CONF_ACCOUNTS]
        ]
    )
    async_add_devices(devices)
    return True


class SIABinarySensor(BinarySensorEntity, RestoreEntity):
    """Class for SIA Binary Sensors."""

    def __init__(
        self,
        entity_id: str,
        name: str,
        port: int,
        account: str,
        zone: int,
        ping_interval: int,
        device_class: str,
    ):
        """Create SIABinarySensor object."""
        self.entity_id = BINARY_SENSOR_FORMAT.format(entity_id)
        self._unique_id = entity_id
        self._name = name
        self._device_class = device_class
        self._port = port
        self._account = account
        self._zone = zone
        self._ping_interval = GET_PING_INTERVAL(ping_interval)
        self._event_listener_str = f"{SIA_EVENT}_{port}_{account}"
        self._unsub = None

        self._should_poll = False
        self._is_on = None
        self._is_available = True
        self._remove_unavailability_tracker = None
        self._attr = {
            CONF_ACCOUNT: self._account,
            CONF_PING_INTERVAL: self.ping_interval,
            CONF_ZONE: self._zone,
            ATTR_LAST_MESSAGE: None,
            ATTR_LAST_CODE: None,
            ATTR_LAST_TIMESTAMP: None,
        }

    async def async_added_to_hass(self):
        """Add sensor to HASS."""
        await super().async_added_to_hass()
        state = await self.async_get_last_state()
        if state is not None and state.state is not None:
            if state.state == STATE_ON:
                self._is_on = True
            elif state.state == STATE_OFF:
                self._is_on = False
        await self._async_track_unavailable()
        async_dispatcher_connect(
            self.hass, DATA_UPDATED, self._schedule_immediate_update
        )
        self._unsub = self.hass.bus.async_listen(
            self._event_listener_str, self.async_handle_event
        )
        self.async_on_remove(self._sia_on_remove)

    @callback
    def _sia_on_remove(self):
        """Remove the unavailability and event listener."""
        if self._unsub:
            self._unsub()
        if self._remove_unavailability_tracker:
            self._remove_unavailability_tracker()

    @callback
    def _schedule_immediate_update(self):
        """Schedule update."""
        self.async_schedule_update_ha_state(True)

    async def async_handle_event(self, event: Event):
        """Listen to events for this port and account and update states.

        If the port and account combo receives any message it means it is online and can therefore be set to available.
        """
        await self.assume_available()
        if (
            int(event.data[EVENT_ZONE]) == self._zone
            or self._device_class == DEVICE_CLASS_POWER
        ):
            device_class, new_state = CODE_CONSEQUENCES.get(
                event.data[EVENT_CODE], (None, None)
            )
            if new_state is not None and device_class == self._device_class:
                self._attr.update(
                    {
                        ATTR_LAST_MESSAGE: event.data[EVENT_MESSAGE],
                        ATTR_LAST_CODE: event.data[EVENT_CODE],
                        ATTR_LAST_TIMESTAMP: event.data[EVENT_TIMESTAMP],
                    }
                )
                self.state = new_state

    @property
    def name(self) -> str:
        """Return name."""
        return self._name

    @property
    def ping_interval(self) -> int:
        """Get ping_interval."""
        return str(self._ping_interval)

    @property
    def unique_id(self) -> str:
        """Return unique id."""
        return self._unique_id

    @property
    def account(self) -> str:
        """Return device account."""
        return self._account

    @property
    def available(self) -> bool:
        """Return avalability."""
        return self._is_available

    @property
    def device_state_attributes(self) -> dict:
        """Return attributes."""
        return self._attr

    @property
    def device_class(self) -> str:
        """Return device class."""
        return self._device_class

    @property
    def state(self) -> str:
        """Return the state of the binary sensor."""
        if self.is_on is None:
            return STATE_UNKNOWN
        return STATE_ON if self.is_on else STATE_OFF

    @property
    def is_on(self) -> bool:
        """Return true if the binary sensor is on."""
        return self._is_on

    @property
    def should_poll(self) -> bool:
        """Return True if entity has to be polled for state.

        False if entity pushes its state to HA.
        """
        return False

    @state.setter
    def state(self, new_on: bool):
        """Set state."""
        self._is_on = new_on
        if not self.registry_entry.disabled:
            self.async_schedule_update_ha_state()

    async def assume_available(self):
        """Reset unavalability tracker."""
        if not self.registry_entry.disabled:
            await self._async_track_unavailable()

    @callback
    async def _async_track_unavailable(self) -> bool:
        """Track availability."""
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
        """Set unavailable."""
        self._remove_unavailability_tracker = None
        self._is_available = False
        self.async_schedule_update_ha_state()

    @property
    def device_info(self) -> dict:
        """Return the device_info."""
        return {
            "identifiers": {(DOMAIN, self.unique_id)},
            "name": self.name,
            "via_device": (DOMAIN, self._port, self._account),
        }
