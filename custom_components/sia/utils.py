from datetime import timedelta
from typing import Tuple

from homeassistant.const import DEVICE_CLASS_TIMESTAMP
from pysiaalarm import SIAEvent

from .const import (
    HUB_SENSOR_NAME,
    HUB_ZONE,
    EVENT_ACCOUNT,
    EVENT_CODE,
    EVENT_ID,
    EVENT_ZONE,
    EVENT_MESSAGE,
    EVENT_TIMESTAMP,
)


def get_entity_and_name(
    port: int, account: str, zone: int = 0, entity_type: str = None
) -> Tuple[str, str]:
    """Give back a entity_id and name according to the variables."""
    if zone == HUB_ZONE:
        entity_type_name = (
            "Last Heartbeat" if entity_type == DEVICE_CLASS_TIMESTAMP else "Power"
        )
        return (
            get_entity_id(port, account, zone, entity_type),
            f"{port} - {account} - {entity_type_name}",
        )
    if entity_type:
        return (
            get_entity_id(port, account, zone, entity_type),
            f"{port} - {account} - zone {zone} - {entity_type}",
        )
    return None


def get_ping_interval(ping: int) -> timedelta:
    """Return the ping interval as timedelta."""
    return timedelta(minutes=ping)


def get_entity_id(
    port: int, account: str, zone: int = 0, entity_type: str = None
) -> str:
    """Give back a entity_id according to the variables, defaults to the hub sensor entity_id."""
    if zone == HUB_ZONE:
        if entity_type == DEVICE_CLASS_TIMESTAMP:
            return f"{port}_{account}_{HUB_SENSOR_NAME}"
        return f"{port}_{account}_{entity_type}"
    if entity_type:
        return f"{port}_{account}_{zone}_{entity_type}"
    return None


def sia_event_to_attr(event: SIAEvent) -> dict:
    """Create the attributes dict from a SIAEvent."""
    return {
        EVENT_ACCOUNT: event.account,
        EVENT_ZONE: event.ri,
        EVENT_CODE: event.code,
        EVENT_MESSAGE: event.message,
        EVENT_ID: event.id,
        EVENT_TIMESTAMP: event.timestamp,
    }
