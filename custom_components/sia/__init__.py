"""The sia integration."""
import asyncio

from homeassistant.components.alarm_control_panel import (
    DOMAIN as ALARM_CONTROL_PANEL_DOMAIN,
)
from homeassistant.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN
from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .const import DOMAIN
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

    hass.data[DOMAIN][entry.entry_id] = hub
    try:
        await hub.sia_client.start(reuse_port=True)
    except OSError:
        raise ConfigEntryNotReady(
            "SIA Server at port %s could not start.", entry.data[CONF_PORT]
        )

    for component in PLATFORMS:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(entry, component)
        )
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
    if unload_ok:
        hub: SIAHub = hass.data[DOMAIN].pop(entry.entry_id)
        await hub.async_shutdown()
    return unload_ok
