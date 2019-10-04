"""Module for SIA Hub."""

import asyncio
import base64
from binascii import hexlify, unhexlify
from collections import defaultdict
from datetime import datetime, timedelta
import json
import logging
import random
import re
import socketserver
import string
import sys
import threading
from threading import Thread
import time

from Crypto import Random
from Crypto.Cipher import AES
import requests
from requests_toolbelt.utils import dump
import sseclient
import voluptuous as vol

from homeassistant.components.alarm_control_panel import (
    ENTITY_ID_FORMAT as ALARM_FORMAT,
    AlarmControlPanel,
)
from homeassistant.components.binary_sensor import (
    DEVICE_CLASS_MOISTURE,
    DEVICE_CLASS_SMOKE,
    ENTITY_ID_FORMAT as BINARY_SENSOR_FORMAT,
    BinarySensorDevice,
)
from homeassistant.components.sensor import ENTITY_ID_FORMAT as SENSOR_FORMAT
from homeassistant.const import (
    ATTR_FRIENDLY_NAME,
    CONF_NAME,
    CONF_PORT,
    CONF_SENSORS,
    CONF_ZONE,
    DEVICE_CLASS_TIMESTAMP,
    STATE_ALARM_ARMED_AWAY,
    STATE_ALARM_ARMED_CUSTOM_BYPASS,
    STATE_ALARM_ARMED_NIGHT,
    STATE_ALARM_DISARMED,
    STATE_ALARM_TRIGGERED,
    STATE_OFF,
    STATE_ON,
)
from homeassistant.core import callback
from homeassistant.exceptions import TemplateError
from homeassistant.helpers import discovery
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity import Entity, generate_entity_id
from homeassistant.helpers.event import (
    async_track_point_in_utc_time,
    async_track_state_change,
)
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.util.dt import utcnow

_LOGGER = logging.getLogger(__name__)

DOMAIN = "sia"

CONF_ACCOUNT = "account"
CONF_ENCRYPTION_KEY = "encryption_key"
CONF_HUBS = "hubs"
CONF_PING_INTERVAL = "ping_interval"
CONF_ZONES = "zones"

DEVICE_CLASS_ALARM = "alarm"
HUB_SENSOR_NAME = "_last_heartbeat"
HUB_ZONE = 0

TYPES = [DEVICE_CLASS_ALARM, DEVICE_CLASS_MOISTURE, DEVICE_CLASS_SMOKE]

ZONE_CONFIG = vol.Schema(
    {
        vol.Optional(CONF_ZONE, default=1): cv.positive_int,
        vol.Optional(CONF_NAME): cv.string,
        vol.Optional(CONF_SENSORS, default=[DEVICE_CLASS_ALARM]): vol.All(
            cv.ensure_list, [vol.In(TYPES)]
        ),
    }
)

HUB_CONFIG = vol.Schema(
    {
        vol.Required(CONF_NAME): cv.string,
        vol.Required(CONF_ACCOUNT): cv.string,
        vol.Optional(CONF_ENCRYPTION_KEY): cv.string,
        vol.Optional(CONF_PING_INTERVAL, default=1): vol.All(
            vol.Coerce(int), vol.Range(min=1, max=1440)
        ),
        vol.Optional(CONF_ZONES, default=[]): vol.All(cv.ensure_list, [ZONE_CONFIG]),
    }
)

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required(CONF_PORT): cv.string,
                vol.Required(CONF_HUBS, default={}): vol.All(
                    cv.ensure_list, [HUB_CONFIG]
                ),
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)

ID_R = "\r".encode()

PING_INTERVAL_MARGIN = timedelta(seconds=30)

HASS_PLATFORM = None

# final import here, because they rely on variables above
from .sia_event import SIAEvent
from .alarm_control_panel import SIAAlarmControlPanel
from .binary_sensor import SIABinarySensor
from .sensor import SIASensor


def setup(hass, config):
    """Implementation of setup from HA."""
    global HASS_PLATFORM
    socketserver.TCPServer.allow_reuse_address = True
    HASS_PLATFORM = hass

    HASS_PLATFORM.data[DOMAIN] = {}

    port = int(config[DOMAIN][CONF_PORT])

    for hub_config in config[DOMAIN][CONF_HUBS]:
        hass.data[DOMAIN][hub_config[CONF_ACCOUNT]] = Hub(hass, hub_config)

    for component in ["binary_sensor", "alarm_control_panel", "sensor"]:
        discovery.load_platform(hass, component, DOMAIN, {}, config)

    for hub in HASS_PLATFORM.data[DOMAIN].values():
        for sensor in hub._states.values():
            sensor.async_schedule_update_ha_state()

    server = socketserver.TCPServer(("", port), AlarmTCPHandler)

    server_thread = threading.Thread(target=server.serve_forever)
    server_thread.start()

    return True


class Hub:
    """Class for SIA Hubs."""

    sensor_types_classes = {
        DEVICE_CLASS_ALARM: "SIAAlarmControlPanel",
        DEVICE_CLASS_MOISTURE: "SIABinarySensor",
        DEVICE_CLASS_SMOKE: "SIABinarySensor",
        DEVICE_CLASS_TIMESTAMP: "SIASensor",
    }

    # main set of responses to certain codes from SIA (see sia_codes for all of them)
    reactions = {
        "BA": {"type": DEVICE_CLASS_ALARM, "new_state": STATE_ALARM_TRIGGERED},
        "BR": {"type": DEVICE_CLASS_ALARM, "new_state": STATE_ALARM_DISARMED},
        "CA": {"type": DEVICE_CLASS_ALARM, "new_state": STATE_ALARM_ARMED_AWAY},
        "CF": {
            "type": DEVICE_CLASS_ALARM,
            "new_state": STATE_ALARM_ARMED_CUSTOM_BYPASS,
        },
        "CG": {"type": DEVICE_CLASS_ALARM, "new_state": STATE_ALARM_ARMED_AWAY},
        "CL": {"type": DEVICE_CLASS_ALARM, "new_state": STATE_ALARM_ARMED_AWAY},
        "CP": {"type": DEVICE_CLASS_ALARM, "new_state": STATE_ALARM_ARMED_AWAY},
        "CQ": {"type": DEVICE_CLASS_ALARM, "new_state": STATE_ALARM_ARMED_AWAY},
        "GA": {"type": DEVICE_CLASS_SMOKE, "new_state": True},
        "GH": {"type": DEVICE_CLASS_SMOKE, "new_state": False},
        "NL": {"type": DEVICE_CLASS_ALARM, "new_state": STATE_ALARM_ARMED_NIGHT},
        "OA": {"type": DEVICE_CLASS_ALARM, "new_state": STATE_ALARM_DISARMED},
        "OG": {"type": DEVICE_CLASS_ALARM, "new_state": STATE_ALARM_DISARMED},
        "OP": {"type": DEVICE_CLASS_ALARM, "new_state": STATE_ALARM_DISARMED},
        "OQ": {"type": DEVICE_CLASS_ALARM, "new_state": STATE_ALARM_DISARMED},
        "OR": {"type": DEVICE_CLASS_ALARM, "new_state": STATE_ALARM_DISARMED},
        "RP": {"type": DEVICE_CLASS_TIMESTAMP, "new_state_eval": "utcnow()"},
        "TA": {"type": DEVICE_CLASS_ALARM, "new_state": STATE_ALARM_TRIGGERED},
        "WA": {"type": DEVICE_CLASS_MOISTURE, "new_state": True},
        "WH": {"type": DEVICE_CLASS_MOISTURE, "new_state": False},
        "YG": {"type": DEVICE_CLASS_TIMESTAMP, "attr": True},
    }

    def __init__(self, hass, hub_config):
        self._name = hub_config[CONF_NAME]
        self._account_id = hub_config[CONF_ACCOUNT]
        self._hass = hass
        self._states = {}
        self._zones = [dict(z) for z in hub_config.get(CONF_ZONES)]
        self._ping_interval = timedelta(minutes=hub_config.get(CONF_PING_INTERVAL))
        self._encrypted = False
        self._ending = "]"
        self._key = hub_config.get(CONF_ENCRYPTION_KEY)
        if self._key:
            _LOGGER.debug("Hub: init: encryption is enabled.")
            self._encrypted = True
            self._key = self._key.encode("utf8")
            # IV standards from https://manualzz.com/doc/11555754/sia-digital-communication-standard-%E2%80%93-internet-protocol-ev...
            # page 12 specifies the decrytion IV to all zeros.
            self._decrypter = AES.new(
                self._key, AES.MODE_CBC, unhexlify("00000000000000000000000000000000")
            )
            _encrypter = AES.new(
                self._key, AES.MODE_CBC, Random.new().read(AES.block_size)
            )
            self._ending = (
                hexlify(_encrypter.encrypt("00000000000000|]".encode("utf8")))
                .decode(encoding="UTF-8")
                .upper()
            )
        # add sensors for each zone as specified in the config.
        for zone in self._zones:
            for sensor in zone.get(CONF_SENSORS):
                self._upsert_sensor(zone.get(CONF_ZONE), sensor)
        # create the hub sensor
        self._upsert_sensor(HUB_ZONE, DEVICE_CLASS_TIMESTAMP)

    def _upsert_sensor(self, zone, sensor_type):
        """ checks if the entity exists, and creates otherwise. always gives back the entity_id """
        sensor_id = self._get_id(zone, sensor_type)
        if not (sensor_id in self._states.keys()):
            zone_found = False
            for existing_zone in self._zones:
                # if the zone exists then a sensor is missing,
                # so, get the zone and add the missing sensor
                if existing_zone[CONF_ZONE] == zone:
                    existing_zone[CONF_SENSORS].append(sensor_type)
                    zone_found = True
                    break
            if not zone_found:
                # if zone does not exist, add it with the sensor and no name
                self._zones.append({CONF_ZONE: zone, CONF_SENSORS: [sensor_type]})

            # add the new sensor
            sensor_name = self._get_sensor_name(zone, sensor_type)
            constructor = self.sensor_types_classes.get(sensor_type)
            _LOGGER.debug(
                "Hub: upsert_sensor: Updating sensor: "
                + sensor_name
                + ", id: "
                + sensor_id
                + ", with constructor: "
                + constructor
            )
            if constructor and sensor_name:
                new_sensor = eval(constructor)(
                    sensor_id,
                    sensor_name,
                    sensor_type,
                    zone,
                    self._ping_interval,
                    self._hass,
                )
                _LOGGER.debug("Hub: upsert_sensor: created sensor: " + str(new_sensor))
                self._states[sensor_id] = new_sensor
            else:
                _LOGGER.warning(
                    "Hub: Upsert Sensor: Unknown device type: %s", sensor_type
                )
        return sensor_id

    def _get_id(self, zone=0, sensor_type=None):
        """ Gives back a entity_id according to the variables, defaults to the hub sensor entity_id. """
        if str(zone) == "0":
            return self._name + HUB_SENSOR_NAME
        else:
            if sensor_type:
                return self._name + "_" + str(zone) + "_" + sensor_type
            else:
                _LOGGER.error(
                    "Hub: Get ID: Not allowed to create an entity_id without type, unless zone == 0."
                )

    def _get_sensor_name(self, zone=0, sensor_type=None):
        """ Gives back a entity_id according to the variables, defaults to the hub sensor entity_id. """
        zone = int(zone)
        if zone == 0:
            return self._name + " Last heartbeat"
        else:
            zone_name = self._get_zone_name(zone)
            if sensor_type:
                return (
                    self._name
                    + (" " + zone_name + " " if zone_name else " ")
                    + sensor_type
                )
            else:
                _LOGGER.error(
                    "Hub: Get Sensor Name: Not allowed to create an entity_id without type, unless zone == 0."
                )
                return None

    def _get_zone_name(self, zone: int):
        return next(
            (z.get(CONF_NAME) for z in self._zones if z.get(CONF_ZONE) == zone), None
        )

    def _update_states(self, event):
        """ Updates the sensors."""
        # find the reactions for that code (if any)
        reaction = self.reactions.get(event.code)
        if reaction:
            # get the entity_id (or create it)
            sensor_id = self._upsert_sensor(event.zone, reaction["type"])
            # find out which action to take, update attribute, new state or eval for new state
            attr = reaction.get("attr")
            new_state = reaction.get("new_state")
            new_state_eval = reaction.get("new_state_eval")
            # do the work (can be more than 1)
            if new_state or new_state_eval:
                _LOGGER.debug(
                    "Hub: Update States: Will set state for entity: "
                    + sensor_id
                    + " to state: "
                    + (new_state if new_state else new_state_eval)
                )
                self._states[sensor_id].state = (
                    new_state if new_state else eval(new_state_eval)
                )
            if attr:
                _LOGGER.debug(
                    "Hub: Update States: Will set attribute entity: %s", sensor_id
                )
                self._states[sensor_id].add_attribute(
                    {
                        "Last message": utcnow().isoformat()
                        + ": SIA: "
                        + event.sia_string
                        + ", Message: "
                        + event.message
                    }
                )
        else:
            _LOGGER.warning(
                "Hub: Update States: Unhandled event type: "
                + event.sia_string
                + ", Message: "
                + event.message
            )
        # whenever a message comes in, the connection is good, so reset the availability timer for all devices.
        for sensor in self._states.values():
            sensor.assume_available()

    def process_event(self, event):
        """Process the Event that comes from the TCP handler."""
        try:
            _LOGGER.debug("Hub: Process event: %s", event)
            if self._encrypted:
                self._decrypt_string(event)
                _LOGGER.debug("Hub: Process event, after decrypt: %s", event)
            self._update_states(event)
        except Exception as exc:
            _LOGGER.error("Hub: Process Event: %s gave error %s", event, str(exc))

        # Even if decrypting or something else gives an error, create the acknowledgement message.
        return '"ACK"{}L0#{}[{}'.format(event.sequence, self._account_id, self._ending)

    def _decrypt_string(self, event):
        """Decrypt the encrypted event content and parse it."""
        _LOGGER.debug("Hub: Decrypt String: Original: %s", str(event.encrypted_content))
        resmsg = self._decrypter.decrypt(unhexlify(event.encrypted_content)).decode(
            encoding="UTF-8", errors="replace"
        )
        _LOGGER.debug("Hub: Decrypt String: Decrypted: %s", resmsg)
        event.parse_decrypted(resmsg)


class AlarmTCPHandler(socketserver.BaseRequestHandler):
    """Class for the TCP Handler."""

    _received_data = "".encode()

    def handle_line(self, line):
        """Method called for each line that comes in."""
        _LOGGER.debug("TCP: Handle Line: Income raw string: %s", line)
        try:
            event = SIAEvent(line)
            _LOGGER.debug("TCP: Handle Line: event: %s", str(event))
            if not event.valid_message:
                _LOGGER.error(
                    "TCP: Handle Line: CRC mismatch, received: %s, calculated: %s",
                    event.msg_crc,
                    event.calc_crc,
                )
                raise Exception("CRC mismatch")
            if event.account not in HASS_PLATFORM.data[DOMAIN]:
                _LOGGER.error(
                    "TCP: Handle Line: Not supported account %s", event.account
                )
                raise Exception(
                    "TCP: Handle Line: Not supported account {}".format(event.account)
                )
            response = HASS_PLATFORM.data[DOMAIN][event.account].process_event(event)
        except Exception as exc:
            _LOGGER.error("TCP: Handle Line: error: %s", str(exc))
            timestamp = datetime.fromtimestamp(time.time()).strftime(
                "_%H:%M:%S,%m-%d-%Y"
            )
            response = '"NAK"0000L0R0A0[]' + timestamp

        header = ("%04x" % len(response)).upper()
        response = "\n{}{}{}\r".format(
            AlarmTCPHandler.crc_calc(response), header, response
        )
        byte_response = str.encode(response)
        self.request.sendall(byte_response)

    def handle(self):
        """Method called for handling."""
        line = b""
        try:
            while True:
                raw = self.request.recv(1024)
                if not raw:
                    return
                raw = bytearray(raw)
                while True:
                    splitter = raw.find(b"\r")
                    if splitter > -1:
                        line = raw[1:splitter]
                        raw = raw[splitter + 1 :]
                    else:
                        break

                    self.handle_line(line.decode())
        except Exception as exc:
            _LOGGER.error(
                "TCP: Handle: last line %s gave error: %s", line.decode(), str(exc)
            )
            return

    @staticmethod
    def crc_calc(msg):
        """Calculate the CRC of the response."""
        new_crc = 0
        for letter in msg:
            temp = ord(letter)
            for _ in range(0, 8):
                temp ^= new_crc & 1
                new_crc >>= 1
                if (temp & 1) != 0:
                    new_crc ^= 0xA001
                temp >>= 1

        return ("%x" % new_crc).upper().zfill(4)
