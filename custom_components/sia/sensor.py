"""Module for SIA Sensors."""
import datetime as dt
import logging
from typing import Callable

from homeassistant.components.sensor import ENTITY_ID_FORMAT as SENSOR_FORMAT
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PORT, CONF_ZONE, DEVICE_CLASS_TIMESTAMP
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.util.dt import utcnow
from pysiaalarm import SIAEvent

from .const import (
    CONF_ACCOUNT,
    CONF_ACCOUNTS,
    CONF_PING_INTERVAL,
    DATA_UPDATED,
    DOMAIN,
    HUB_ZONE,
    SIA_EVENT,
)
from .helpers import GET_ENTITY_AND_NAME, GET_PING_INTERVAL, SIA_EVENT_TO_ATTR

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: Callable[[], None]
) -> bool:
    """Set up sia_sensor from a config entry."""
    async_add_entities(
        [
            SIASensor(
                *GET_ENTITY_AND_NAME(
                    entry.data[CONF_PORT],
                    acc[CONF_ACCOUNT],
                    HUB_ZONE,
                    DEVICE_CLASS_TIMESTAMP,
                ),
                entry.data[CONF_PORT],
                acc[CONF_ACCOUNT],
                HUB_ZONE,
                acc[CONF_PING_INTERVAL],
                DEVICE_CLASS_TIMESTAMP,
            )
            for acc in entry.data[CONF_ACCOUNTS]
        ]
    )
    return True


class SIASensor(RestoreEntity):
    """Class for SIA Sensors."""

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
        """Create SIASensor object."""
        self.entity_id = SENSOR_FORMAT.format(entity_id)
        self._unique_id = entity_id
        self._name = name
        self._device_class = device_class
        self._port = port
        self._account = account
        self._zone = zone
        self._ping_interval = GET_PING_INTERVAL(ping_interval)
        self._event_listener_str = f"{SIA_EVENT}_{port}_{account}"
        self._unsub = None

        self._state = utcnow()
        self._attr = {
            CONF_ACCOUNT: self._account,
            CONF_PING_INTERVAL: self.ping_interval,
            CONF_ZONE: self._zone,
        }

    async def async_added_to_hass(self) -> None:
        """Once the sensor is added, see if it was there before and pull in that state."""
        await super().async_added_to_hass()
        state = await self.async_get_last_state()
        if state is not None and state.state is not None:
            self.state = dt.datetime.strptime(state.state, "%Y-%m-%dT%H:%M:%S.%f%z")

        async_dispatcher_connect(self.hass, DATA_UPDATED, self.async_write_ha_state)
        self._unsub = self.hass.bus.async_listen(
            self._event_listener_str, self.async_handle_event
        )
        self.async_on_remove(self._async_sia_on_remove)

    @callback
    def _async_sia_on_remove(self):
        """Remove the event listener."""
        if self._unsub:
            self._unsub()

    async def async_handle_event(self, event: Event):
        """Listen to events for this port and account and update the state and attributes."""
        sia_event = SIAEvent.from_dict(event.data)
        sia_event.message_type = sia_event.message_type.value
        self._attr.update(sia_event.to_dict())
        if sia_event.code == "RP":
            self.state = utcnow()
        if self.enabled:
            self.async_schedule_update_ha_state()

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
        """Get unique_id."""
        return self._unique_id

    @property
    def state(self) -> str:
        """Return state."""
        return self._state.isoformat()

    @property
    def account(self) -> str:
        """Return device account."""
        return self._account

    @property
    def device_state_attributes(self) -> dict:
        """Return attributes."""
        return self._attr

    @property
    def should_poll(self) -> bool:
        """Return False if entity pushes its state to HA."""
        return False

    @property
    def device_class(self) -> str:
        """Return device class."""
        return self._device_class

    @state.setter
    def state(self, state: dt.datetime):
        """Set state."""
        self._state = state

    @property
    def icon(self) -> str:
        """Return the icon to use in the frontend, if any."""
        return "mdi:alarm-light-outline"

    @property
    def unit_of_measurement(self) -> str:
        """Return the unit of measurement."""
        return "ISO8601"

    @property
    def device_info(self) -> dict:
        """Return the device_info."""
        return {
            "identifiers": {(DOMAIN, self.unique_id)},
            "name": self.name,
            "via_device": (DOMAIN, self._port, self._account),
        }
