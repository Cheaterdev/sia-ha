"""The sia integration."""
import asyncio

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.const import EVENT_HOMEASSISTANT_STOP
from homeassistant.components.alarm_control_panel import (
    DOMAIN as ALARM_CONTROL_PANEL_DOMAIN,
)
from homeassistant.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN
from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN

from .const import DOMAIN, SIA_HUB, DATA_UNSUBSCRIBE
from .hub import SIAHub


PLATFORMS = [ALARM_CONTROL_PANEL_DOMAIN, BINARY_SENSOR_DOMAIN, SENSOR_DOMAIN]


async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the sia component."""
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up sia from a config entry."""
    hub = SIAHub(hass, entry.data, entry.entry_id, entry.title)

    await hub.async_setup_hub()

    unsub = hass.bus.async_listen(EVENT_HOMEASSISTANT_STOP, hub.async_shutdown)

    hass.data[DOMAIN][entry.entry_id] = {
        SIA_HUB: hub,
        DATA_UNSUBSCRIBE: unsub,
    }
    for component in PLATFORMS:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(entry, component)
        )
    hub.sia_client.start(reuse_port=True)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""
    unload_ok = all(
        await asyncio.gather(
            *[
                hass.config_entries.async_forward_entry_unload(entry, component)
                for component in PLATFORMS
            ]
        )
    )
    info = hass.data[DOMAIN].pop(entry.entry_id)

    info[DATA_UNSUBSCRIBE]()
    await info[SIA_HUB].sia_client.stop()

    return unload_ok
