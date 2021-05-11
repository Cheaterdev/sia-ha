"""The sia hub."""
import logging

from homeassistant.const import CONF_PORT, CONF_PROTOCOL, EVENT_HOMEASSISTANT_STOP
from homeassistant.core import Event, EventOrigin, HomeAssistant
from homeassistant.helpers import device_registry as dr
from pysiaalarm.aio import SIAAccount, SIAClient, SIAEvent, CommunicationsProtocol

from .const import (
    CONF_ACCOUNT,
    CONF_ACCOUNTS,
    CONF_ENCRYPTION_KEY,
    CONF_IGNORE_TIMESTAMPS,
    DOMAIN,
    SIA_EVENT,
    IGNORED_TIMEBAND,
    DEFAULT_TIMEBAND,
)


_LOGGER = logging.getLogger(__name__)


class SIAHub:
    """Class for SIA Hubs."""

    def __init__(
        self, hass: HomeAssistant, hub_config: dict, entry_id: str, title: str
    ):
        """Create the SIAHub."""
        self._hass = hass
        self._port = int(hub_config[CONF_PORT])
        self.entry_id = entry_id
        self._title = title
        self._accounts = hub_config[CONF_ACCOUNTS]
        self._protocol = hub_config[CONF_PROTOCOL]

        self._remove_shutdown_listener = None
        self.sia_accounts = [
            SIAAccount(
                a[CONF_ACCOUNT],
                a.get(CONF_ENCRYPTION_KEY),
                IGNORED_TIMEBAND
                if a.get(CONF_IGNORE_TIMESTAMPS, False)
                else DEFAULT_TIMEBAND,
            )
            for a in self._accounts
        ]
        self.sia_client = SIAClient(
            "",
            self._port,
            self.sia_accounts,
            self.async_create_and_fire_event,
            CommunicationsProtocol(self._protocol),
        )

    async def async_setup_hub(self):
        """Add a device to the device_registry, register shutdown listener, load reactions."""
        _LOGGER.debug("Setting up SIA Hub.")
        device_registry = await dr.async_get_registry(self._hass)
        port = self._port
        for acc in self._accounts:
            account = acc[CONF_ACCOUNT]
            device_registry.async_get_or_create(
                config_entry_id=self.entry_id,
                identifiers={(DOMAIN, port, account)},
                name=f"{port} - {account}",
            )
        self._remove_shutdown_listener = self._hass.bus.async_listen(
            EVENT_HOMEASSISTANT_STOP, self.async_shutdown
        )

    async def async_shutdown(self, _: Event = None):
        """Shutdown the SIA server."""
        if self._remove_shutdown_listener:
            self._remove_shutdown_listener()
        await self.sia_client.stop()

    async def async_create_and_fire_event(self, event: SIAEvent):
        """Create a event on HA's bus, with the data from the SIAEvent."""
        self._hass.bus.async_fire(
            event_type=f"{SIA_EVENT}_{self._port}_{event.account}",
            event_data=event.to_dict(encode_json=True),
            origin=EventOrigin.remote,
        )
