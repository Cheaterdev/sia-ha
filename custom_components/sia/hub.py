"""The sia hub."""
import asyncio
from datetime import timedelta
import logging

from pysiaalarm.aio import SIAAccount, SIAClient, SIAEvent

from homeassistant.components.binary_sensor import (
    DEVICE_CLASS_MOISTURE,
    DEVICE_CLASS_SMOKE,
    DEVICE_CLASS_POWER,
)
from homeassistant.const import (
    CONF_PORT,
    CONF_SENSORS,
    CONF_ZONE,
    DEVICE_CLASS_TIMESTAMP,
    EVENT_HOMEASSISTANT_STOP,
)
from homeassistant.core import Event, HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.util.dt import utcnow

from .alarm_control_panel import SIAAlarmControlPanel
from .binary_sensor import SIABinarySensor
from .const import (
    CONF_ACCOUNT,
    CONF_ACCOUNTS,
    CONF_ENCRYPTION_KEY,
    CONF_PING_INTERVAL,
    CONF_ZONES,
    DEVICE_CLASS_ALARM,
    DOMAIN,
    HUB_SENSOR_NAME,
    HUB_ZONE,
    LAST_MESSAGE,
    REACTIONS,
    UTCNOW,
)
from .sensor import SIASensor

_LOGGER = logging.getLogger(__name__)


class SIAHub:
    """Class for SIA Hubs."""

    def __init__(
        self, hass: HomeAssistant, hub_config: dict, entry_id: str, title: str
    ):
        """Create the SIAHub."""
        self._hass = hass
        self.states = {}
        self._port = int(hub_config[CONF_PORT])
        self.entry_id = entry_id
        self._title = title
        self._accounts = hub_config[CONF_ACCOUNTS]
        self.shutdown_remove_listener = None
        self._reactions = REACTIONS

        self._zones = [
            {
                CONF_ACCOUNT: a[CONF_ACCOUNT],
                CONF_ZONE: HUB_ZONE,
                CONF_SENSORS: [DEVICE_CLASS_TIMESTAMP, DEVICE_CLASS_POWER],
            }
            for a in self._accounts
        ]
        self._zones.extend(
            [
                {
                    CONF_ACCOUNT: a[CONF_ACCOUNT],
                    CONF_ZONE: z,
                    CONF_SENSORS: [
                        DEVICE_CLASS_ALARM,
                        DEVICE_CLASS_MOISTURE,
                        DEVICE_CLASS_SMOKE,
                    ],
                }
                for a in self._accounts
                for z in range(1, int(a[CONF_ZONES]) + 1)
            ]
        )

        self.sia_accounts = [
            SIAAccount(a[CONF_ACCOUNT], a.get(CONF_ENCRYPTION_KEY))
            for a in self._accounts
        ]
        self.sia_client = SIAClient(
            "", self._port, self.sia_accounts, self.update_states
        )
        self._create_sensors()

    async def async_setup_hub(self):
        """Add a device to the device_registry, register shutdown listener, load reactions."""
        device_registry = await dr.async_get_registry(self._hass)
        port = self._port
        for acc in self._accounts:
            account = acc[CONF_ACCOUNT]
            device_registry.async_get_or_create(
                config_entry_id=self.entry_id,
                identifiers={(DOMAIN, port, account)},
                name=f"{port} - {account}",
            )
        self.shutdown_remove_listener = self._hass.bus.async_listen_once(
            EVENT_HOMEASSISTANT_STOP, self.async_shutdown
        )

    async def async_shutdown(self, _: Event):
        """Shutdown the SIA server."""
        await self.sia_client.stop()

    def _create_sensors(self):
        """Create all the sensors."""
        for zone in self._zones:
            ping = self._get_ping_interval(zone[CONF_ACCOUNT])
            for entity_type in zone[CONF_SENSORS]:
                self._create_sensor(
                    self._port, zone[CONF_ACCOUNT], zone[CONF_ZONE], entity_type, ping
                )

    def _create_sensor(
        self, port: int, account: str, zone: int, entity_type: str, ping: int
    ):
        """Check if the entity exists, and creates otherwise."""
        entity_id, entity_name = self._get_entity_id_and_name(
            account, zone, entity_type
        )
        if entity_type == DEVICE_CLASS_ALARM:
            self.states[entity_id] = SIAAlarmControlPanel(
                entity_id, entity_name, port, account, zone, ping
            )
            return
        if entity_type in (DEVICE_CLASS_MOISTURE, DEVICE_CLASS_SMOKE, DEVICE_CLASS_POWER):
            self.states[entity_id] = SIABinarySensor(
                entity_id, entity_name, entity_type, port, account, zone, ping
            )
            return
        if entity_type == DEVICE_CLASS_TIMESTAMP:
            self.states[entity_id] = SIASensor(
                entity_id, entity_name, entity_type, port, account, zone, ping
            )

    def _get_entity_id_and_name(
        self, account: str, zone: int = 0, entity_type: str = None
    ):
        """Give back a entity_id and name according to the variables."""
        if zone == 0:
            entity_type_name = "Last Heartbeat" if entity_type == DEVICE_CLASS_TIMESTAMP else "Power"
            return (
                self._get_entity_id(account, zone, entity_type),
                f"{self._port} - {account} - {entity_type_name}",
            )
        if entity_type:
            return (
                self._get_entity_id(account, zone, entity_type),
                f"{self._port} - {account} - zone {zone} - {entity_type}",
            )
        return None

    def _get_entity_id(self, account: str, zone: int = 0, entity_type: str = None):
        """Give back a entity_id according to the variables, defaults to the hub sensor entity_id."""
        if zone == 0:
            if entity_type == DEVICE_CLASS_TIMESTAMP:
                return f"{self._port}_{account}_{HUB_SENSOR_NAME}"
            return f"{self._port}_{account}_{entity_type}"
        if entity_type:
            return f"{self._port}_{account}_{zone}_{entity_type}"
        return None

    def _get_ping_interval(self, account: str):
        """Return the ping interval for specified account."""
        for acc in self._accounts:
            if acc[CONF_ACCOUNT] == account:
                return timedelta(minutes=acc[CONF_PING_INTERVAL])
        return None

    async def update_states(self, event: SIAEvent):
        """Update the sensors. This can be both a new state and a new attribute.

        Whenever a message comes in and is a event that should cause a reaction, the connection is good, so reset the availability timer for all devices of that account, excluding the last heartbeat.

        """

        # ignore exceptions (those are returned now, but not read) to deal with disabled sensors.
        await asyncio.gather(
            *[
                entity.assume_available()
                for entity in self.states.values()
                if entity.account == event.account and not isinstance(entity, SIASensor)
            ],
            return_exceptions=True,
        )

        # find the reactions for that code (if any)
        reaction = self._reactions.get(event.code)
        if not reaction:
            _LOGGER.info(
                "Unhandled event code, will be set as attribute in the heartbeat sensor. Code is: %s, Message: %s, Full event: %s",
                event.code,
                event.message,
                event.sia_string,
            )
            reaction = {"type": DEVICE_CLASS_TIMESTAMP, "attr": LAST_MESSAGE}
        attr = reaction.get("attr")
        new_state = reaction.get("new_state")
        new_state_eval = reaction.get("new_state_eval")
        entity_id = self._get_entity_id(
            event.account, int(event.ri), reaction["type"]
        )

        #update state
        if new_state is not None:
            self.states[entity_id].state = new_state
        elif new_state_eval is not None:
            if new_state_eval == UTCNOW:
                self.states[entity_id].state = utcnow()

        #update standard attributes of the touched sensor and if necessary the last_message or other attributes
        self.states[entity_id].add_attribute( { "last_message": {event.message} })
        self.states[entity_id].add_attribute( { "last_code": {event.code} })
        self.states[entity_id].add_attribute( { "last_update": {utcnow().isoformat()} })
        if attr is not None:
            if attr == LAST_MESSAGE:
                self.states[entity_id].add_attribute(
                    {
                        "last_sia_event_string": "SIA: {event.sia_string}"                        
                    }
                )
