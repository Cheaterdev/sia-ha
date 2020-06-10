"""The sia integration."""
import asyncio
from datetime import timedelta
import logging

from pysiaalarm.aio import SIAAccount, SIAClient, SIAEvent

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_PORT,
    CONF_SENSORS,
    CONF_ZONE,
    EVENT_HOMEASSISTANT_STOP,
)
from homeassistant.core import HomeAssistant
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
    DEVICE_CLASS_MOISTURE,
    DEVICE_CLASS_SMOKE,
    DEVICE_CLASS_TIMESTAMP,
    DOMAIN,
    HUB_SENSOR_NAME,
    HUB_ZONE,
    LAST_MESSAGE,
    PLATFORMS,
    REACTIONS,
    UTCNOW,
)
from .sensor import SIASensor

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the sia component."""
    hass.data[DOMAIN] = {}
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up sia from a config entry."""
    hass.data[DOMAIN][entry.entry_id] = SIAHub(
        hass, entry.data, entry.entry_id, entry.title
    )
    await hass.data[DOMAIN][entry.entry_id].async_setup_hub()
    for component in PLATFORMS:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(entry, component)
        )
    hass.data[DOMAIN][entry.entry_id].sia_client.start(reuse_port=True)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""

    await hass.data[DOMAIN][entry.entry_id].sia_client.stop()
    hass.data[DOMAIN][entry.entry_id].shutdown_remove_listener()
    unload_ok = all(
        await asyncio.gather(
            *[
                hass.config_entries.async_forward_entry_unload(entry, component)
                for component in PLATFORMS
            ]
        )
    )

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


class SIAHub:
    """Class for SIA Hubs."""

    def __init__(self, hass, hub_config, entry_id, title):
        """Create the SIAHub."""
        self._hass = hass
        self.states = {}
        self._port = int(hub_config[CONF_PORT])
        self.entry_id = entry_id
        self._title = title
        self._accounts = hub_config[CONF_ACCOUNTS]
        self.shutdown_remove_listener = None

        self._zones = [
            {
                CONF_ACCOUNT: a[CONF_ACCOUNT],
                CONF_ZONE: HUB_ZONE,
                CONF_SENSORS: [DEVICE_CLASS_TIMESTAMP],
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

        for zone in self._zones:
            ping = self._get_ping_interval(zone[CONF_ACCOUNT])
            for sensor in zone[CONF_SENSORS]:
                self._create_sensor(
                    self._port, zone[CONF_ACCOUNT], zone[CONF_ZONE], sensor, ping
                )

    async def async_setup_hub(self):
        """Add a device to the device_registry and register shutdown listener."""
        device_registry = await dr.async_get_registry(self._hass)
        port = self._port
        for acc in self._accounts:
            account = acc[CONF_ACCOUNT]
            device_registry.async_get_or_create(
                config_entry_id=self.entry_id,
                identifiers={(DOMAIN, port, account)},
                name=f"{port} - {account}",
            )
        self.shutdown_remove_listener = self.hass.bus.async_listen_once(
            EVENT_HOMEASSISTANT_STOP, self.async_shutdown
        )

    async def async_shutdown(self):
        """Shutdown the SIA server."""
        await self.sia_client.stop()

    def _create_sensor(self, port, account, zone, entity_type, ping):
        """Check if the entity exists, and creates otherwise."""
        entity_id, entity_name = self._get_entity_id_and_name(
            account, zone, entity_type
        )
        if entity_type == DEVICE_CLASS_ALARM:
            new_entity = SIAAlarmControlPanel(
                entity_id, entity_name, port, account, zone, ping, self._hass,
            )
        elif entity_type in (DEVICE_CLASS_MOISTURE, DEVICE_CLASS_SMOKE):
            new_entity = SIABinarySensor(
                entity_id,
                entity_name,
                entity_type,
                port,
                account,
                zone,
                ping,
                self._hass,
            )
        elif entity_type == DEVICE_CLASS_TIMESTAMP:
            new_entity = SIASensor(
                entity_id,
                entity_name,
                entity_type,
                port,
                account,
                zone,
                ping,
                self._hass,
            )
        self.states[entity_id] = new_entity

    def _get_entity_id_and_name(self, account, zone=0, entity_type=None):
        """Give back a entity_id and name according to the variables."""
        if zone == 0:
            return (
                self._get_entity_id(account, zone, entity_type),
                f"{self._port} - {account} - Last Heartbeat",
            )
        else:
            if entity_type:
                return (
                    self._get_entity_id(account, zone, entity_type),
                    f"{self._port} - {account} - zone {zone} - {entity_type}",
                )
            return None

    def _get_entity_id(self, account, zone=0, entity_type=None):
        """Give back a entity_id according to the variables, defaults to the hub sensor entity_id."""
        if zone == 0 or entity_type == DEVICE_CLASS_TIMESTAMP:
            return f"{self._port}_{account}_{HUB_SENSOR_NAME}"
        else:
            if entity_type:
                return f"{self._port}_{account}_{zone}_{entity_type}"
            return None

    def _get_ping_interval(self, account):
        """Return the ping interval for specified account."""
        for acc in self._accounts:
            if acc[CONF_ACCOUNT] == account:
                return timedelta(minutes=acc[CONF_PING_INTERVAL])
        return None

    async def update_states(self, event: SIAEvent):
        """Update the sensors. This can be both a new state and a new attribute.

        Whenever a message comes in and is a event that should cause a reaction, the connection is good, so reset the availability timer for all devices of that account, excluding the last heartbeat.

        """
        # find the reactions for that code (if any)
        reaction = REACTIONS.get(event.code)
        if not reaction:
            _LOGGER.warning(
                "Unhandled event code: %s, Message: %s, Full event: %s",
                event.code,
                event.message,
                event.sia_string,
            )
            return
        attr = reaction.get("attr")
        new_state = reaction.get("new_state")
        new_state_eval = reaction.get("new_state_eval")
        entity_id = self._get_entity_id(
            event.account, int(event.zone), reaction["type"]
        )

        if new_state:
            self.states[entity_id].state = new_state
        elif new_state_eval:
            if new_state_eval == UTCNOW:
                self.states[entity_id].state = utcnow()
        if attr:
            if attr == LAST_MESSAGE:
                self.states[entity_id].add_attribute(
                    {
                        "last_message": f"{utcnow().isoformat()}: SIA: {event.sia_string}, Message: {event.message}"
                    }
                )

        await asyncio.gather(
            *[
                entity.assume_available()
                for entity in self.states.values()
                if entity.account == event.account and not isinstance(entity, SIASensor)
            ]
        )
