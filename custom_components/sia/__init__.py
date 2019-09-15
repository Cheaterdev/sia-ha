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

from .sia_codes import SIACodes

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

ID_STRING = '"SIA-DCS"'.encode()
ID_STRING_ENCODED = '"*SIA-DCS"'.encode()
ID_R = "\r".encode()

PING_INTERVAL_MARGIN = timedelta(seconds=30)

hass_platform = None


def setup(hass, config):
    global hass_platform
    socketserver.TCPServer.allow_reuse_address = True
    hass_platform = hass

    hass_platform.data[DOMAIN] = {}

    port = int(config[DOMAIN][CONF_PORT])

    for hub_config in config[DOMAIN][CONF_HUBS]:
        if CONF_ENCRYPTION_KEY in hub_config:
            hass.data[DOMAIN][hub_config[CONF_ACCOUNT]] = EncryptedHub(hass, hub_config)
        else:
            hass.data[DOMAIN][hub_config[CONF_ACCOUNT]] = Hub(hass, hub_config)

    for component in ["binary_sensor", "alarm_control_panel", "sensor"]:
        discovery.load_platform(hass, component, DOMAIN, {}, config)

    server = socketserver.TCPServer(("", port), AlarmTCPHandler)

    t = threading.Thread(target=server.serve_forever)
    t.start()

    return True


class Hub:

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
        self._accountId = hub_config[CONF_ACCOUNT]
        self._hass = hass
        self._states = {}
        self._zones = hub_config.get(CONF_ZONES)
        self._entity_ids = []
        self._ping_interval = timedelta(minutes=hub_config.get(CONF_PING_INTERVAL))
        # create the hub sensor
        self._upsert_sensor(HUB_ZONE, DEVICE_CLASS_TIMESTAMP)
        # add sensors for each zone as specified in the config.
        for z in self._zones:
            for s in z.get(CONF_SENSORS):
                self._upsert_sensor(z.get(CONF_ZONE), s)

    def _update_states(self, sia, zoneID, message):
        """ Updates the sensors."""
        # find the reactions for that code (if any)
        reaction = self.reactions.get(sia.code)
        if reaction:
            # get the entity_id (or create it)
            entity_id = self._upsert_sensor(zoneID, reaction["type"])
            # find out which action to take, update attribute, new state or eval for new state
            attr = reaction.get("attr")
            new_state = reaction.get("new_state")
            new_state_eval = reaction.get("new_state_eval")
            # do the work (can be more than 1)
            if new_state or new_state_eval:
                _LOGGER.debug(
                    "Will set state for entity: "
                    + entity_id
                    + " to state: "
                    + (new_state if new_state else new_state_eval)
                )
                self._states[entity_id].state = (
                    new_state if new_state else eval(new_state_eval)
                )
            if attr:
                _LOGGER.debug("Will set attribute entity: " + entity_id)
                self._states[entity_id].add_attribute(
                    {
                        "Last message": utcnow().isoformat()
                        + ": SIA: "
                        + str(sia)
                        + ", Message: "
                        + message
                    }
                )
        else:
            _LOGGER.warning(
                "Unhandled event type: " + str(sia) + ", Message: " + message
            )
        # whenever a message comes in, the connection is good, so reset the availability clock for all devices.
        for e in self._entity_ids:
            self._states[e].assume_available()

    def _parse_message(self, msg):
        """ Parses the message and finds the SIA."""
        parts = msg.split("|")[2].split("]")[0].split("/")
        zoneID = parts[0][3:]
        message = parts[1]
        sia = SIACodes(message[0:2])
        _LOGGER.debug(
            "Incoming parsed: "
            + msg
            + " to sia: "
            + str(sia)
            + " for zone: "
            + zoneID
            + " with message: "
            + message
        )
        return sia, zoneID, message

    def _upsert_sensor(self, zone, sensor_type):
        """ checks if the entity exists, and creates otherwise. always gives back the entity_id """
        sensor_name = self._get_sensor_name(zone, sensor_type)
        entity_id = self._get_entity_id(zone, sensor_type)
        if not (entity_id in self._entity_ids):
            zone_found = False
            for z in self._zones:
                # if the zone exists then a sensor is missing,
                # so, get the zone and add the missing sensor
                if z[CONF_ZONE] == zone:
                    z[CONF_SENSORS].append(sensor_type)
                    zone_found = True
                    break
            if not zone_found:
                # if zone does not exist, add it with the sensor and no name
                self._zones.append({CONF_ZONE: zone, CONF_SENSORS: [sensor_type]})

            # add the new sensor
            constructor = self.sensor_types_classes.get(sensor_type)
            if constructor:
                self._states[entity_id] = eval(constructor)(
                    entity_id,
                    sensor_name,
                    sensor_type,
                    zone,
                    self._ping_interval,
                    self._hass,
                )
            else:
                _LOGGER.warning("Unknown device type: " + sensor_type)
            self._entity_ids.append(entity_id)
        return entity_id

    def _get_entity_id(self, zone=0, sensor_type=None):
        """ Gives back a entity_id according to the variables, defaults to the hub sensor entity_id. """
        if str(zone) == "0":
            return self._name + HUB_SENSOR_NAME
        else:
            if sensor_type:
                return self._name + "_" + str(zone) + "_" + sensor_type
            else:
                _LOGGER.error(
                    "Not allowed to create an entity_id without type, unless zone == 0."
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
                    + (" " + zone_name if zone_name else "")
                    + " "
                    + sensor_type
                )
            else:
                _LOGGER.error(
                    "Not allowed to create an entity_id without type, unless zone == 0."
                )

    def _get_zone_name(self, zone: int):
        return next((z.get(CONF_NAME) for z in self._zones if z.get(CONF_ZONE) == zone))

    def process_line(self, line):
        # _LOGGER.debug("Hub.process_line" + line.decode())
        pos = line.find(ID_STRING)
        assert pos >= 0, "Can't find ID_STRING, check encryption configs"
        seq = line[pos + len(ID_STRING) : pos + len(ID_STRING) + 4]
        data = line[line.index(b"[") :]
        # _LOGGER.debug("Hub.process_line found data: " + data.decode())
        self._update_states(*self._parse_message(data.decode()))
        return '"ACK"' + (seq.decode()) + "L0#" + (self._accountId) + "[]"


class EncryptedHub(Hub):
    def __init__(self, hass, hub_config):
        self._key = hub_config[CONF_ENCRYPTION_KEY].encode("utf8")
        iv = Random.new().read(AES.block_size)
        _cipher = AES.new(self._key, AES.MODE_CBC, iv)
        self.iv2 = None
        self._ending = (
            hexlify(_cipher.encrypt("00000000000000|]".encode("utf8")))
            .decode(encoding="UTF-8")
            .upper()
        )
        Hub.__init__(self, hass, hub_config)

    def _manage_string(self, msg):
        iv = unhexlify(
            "00000000000000000000000000000000"
        )  # where i need to find proper IV ? Only this works good.
        _cipher = AES.new(self._key, AES.MODE_CBC, iv)
        data = _cipher.decrypt(unhexlify(msg[1:]))
        # _LOGGER.debug(
        #     "EncryptedHub.manage_string data: "
        #     + data.decode(encoding="UTF-8", errors="replace")
        # )

        data = data[data.index(b"|") :]
        resmsg = data.decode(encoding="UTF-8", errors="replace")
        Hub._update_states(self, *Hub._parse_message(self, resmsg))

    def process_line(self, line):
        # _LOGGER.debug("EncryptedHub.process_line" + line.decode())
        pos = line.find(ID_STRING_ENCODED)
        assert pos >= 0, "Can't find ID_STRING_ENCODED, is SIA encryption enabled?"
        seq = line[pos + len(ID_STRING_ENCODED) : pos + len(ID_STRING_ENCODED) + 4]
        data = line[line.index(b"[") :]
        # _LOGGER.debug("EncryptedHub.process_line found data: " + data.decode())
        self._manage_string(data.decode())
        return (
            '"*ACK"' + (seq.decode()) + "L0#" + (self._accountId) + "[" + self._ending
        )


class SIAAlarmControlPanel(RestoreEntity):
    def __init__(self, entity_id, name, device_class, zone, ping_interval, hass):
        self._should_poll = False
        self.entity_id = generate_entity_id(
            entity_id_format=ALARM_FORMAT, name=entity_id, hass=hass
        )
        self._name = name
        self.hass = hass
        self._ping_interval = ping_interval
        self._attr = {CONF_PING_INTERVAL: self.ping_interval, CONF_ZONE: zone}
        self._is_available = True
        self._remove_unavailability_tracker = None

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        state = await self.async_get_last_state()
        if state is not None and state.state is not None:
            if state.state == STATE_ALARM_ARMED_AWAY:
                self._state = STATE_ALARM_ARMED_AWAY
            elif state.state == STATE_ALARM_ARMED_NIGHT:
                self._state = STATE_ALARM_ARMED_NIGHT
            elif state.state == STATE_ALARM_TRIGGERED:
                self._state = STATE_ALARM_TRIGGERED
            elif state.state == STATE_ALARM_DISARMED:
                self._state = STATE_ALARM_DISARMED
            elif state.state == STATE_ALARM_ARMED_CUSTOM_BYPASS:
                self._state = STATE_ALARM_ARMED_CUSTOM_BYPASS
            else:
                self._state = None
        else:
            self._state = STATE_ALARM_DISARMED  # assume disarmed
        self._async_track_unavailable()

    @property
    def name(self):
        return self._name

    @property
    def ping_interval(self):
        return str(self._ping_interval)

    @property
    def state(self):
        return self._state

    @property
    def unique_id(self) -> str:
        return self._name

    @property
    def available(self):
        return self._is_available

    def alarm_disarm(self, code=None):
        _LOGGER.debug("Not implemented.")

    def alarm_arm_home(self, code=None):
        _LOGGER.debug("Not implemented.")

    def alarm_arm_away(self, code=None):
        _LOGGER.debug("Not implemented.")

    def alarm_arm_night(self, code=None):
        _LOGGER.debug("Not implemented.")

    def alarm_trigger(self, code=None):
        _LOGGER.debug("Not implemented.")

    def alarm_arm_custom_bypass(self, code=None):
        _LOGGER.debug("Not implemented.")

    @property
    def device_state_attributes(self):
        return self._attr

    @state.setter
    def state(self, state):
        self._state = state
        self.async_schedule_update_ha_state()

    def assume_available(self):
        self._async_track_unavailable()

    @callback
    def _async_track_unavailable(self):
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
        self._remove_unavailability_tracker = None
        self._is_available = False
        self.async_schedule_update_ha_state()


class SIABinarySensor(RestoreEntity):
    def __init__(self, entity_id, name, device_class, zone, ping_interval, hass):
        self._device_class = device_class
        self._should_poll = False
        self._ping_interval = ping_interval
        self._attr = {CONF_PING_INTERVAL: self.ping_interval, CONF_ZONE: zone}
        self.entity_id = generate_entity_id(
            entity_id_format=BINARY_SENSOR_FORMAT, name=entity_id, hass=hass
        )
        self._name = name
        self.hass = hass
        self._is_available = True
        self._remove_unavailability_tracker = None

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        state = await self.async_get_last_state()
        if state is not None and state.state is not None:
            self._state = state.state == STATE_ON
        else:
            self._state = None
        self._async_track_unavailable()

    @property
    def name(self):
        return self._name

    @property
    def ping_interval(self):
        return str(self._ping_interval)

    @property
    def state(self):
        return STATE_ON if self.is_on else STATE_OFF

    @property
    def unique_id(self) -> str:
        return self._name

    @property
    def available(self):
        return self._is_available

    @property
    def device_state_attributes(self):
        return self._attr

    @property
    def device_class(self):
        return self._device_class

    @property
    def is_on(self):
        return self._state

    @state.setter
    def state(self, state):
        self._state = state
        self.async_schedule_update_ha_state()

    def assume_available(self):
        self._async_track_unavailable()

    @callback
    def _async_track_unavailable(self):
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
        self._remove_unavailability_tracker = None
        self._is_available = False
        self.async_schedule_update_ha_state()


class SIASensor(Entity):
    def __init__(self, entity_id, name, device_class, zone, ping_interval, hass):
        self._should_poll = False
        self._device_class = device_class
        self.entity_id = generate_entity_id(
            entity_id_format=SENSOR_FORMAT, name=entity_id, hass=hass
        )
        self._state = utcnow()
        self._attr = {CONF_PING_INTERVAL: str(ping_interval), CONF_ZONE: zone}
        self._name = name
        self.hass = hass

    @property
    def name(self):
        return self._name

    @property
    def state(self):
        return self._state.isoformat()

    @property
    def device_state_attributes(self):
        return self._attr

    def add_attribute(self, attr):
        self._attr.update(attr)

    @property
    def device_class(self):
        return self._device_class

    @state.setter
    def state(self, state):
        self._state = state

    def assume_available(self):
        pass

    @property
    def icon(self):
        """Return the icon to use in the frontend, if any."""
        return "mdi:alarm-light-outline"


class AlarmTCPHandler(socketserver.BaseRequestHandler):
    _received_data = "".encode()

    def handle_line(self, line):
        # _LOGGER.debug("Income raw string: " + line.decode())
        accountId = line[line.index(b"#") + 1 : line.index(b"[")].decode()

        pos = line.find(b'"')
        assert pos >= 0, "Can't find message beginning"
        inputMessage = line[pos:]
        msgcrc = line[0:4]
        codecrc = str.encode(AlarmTCPHandler.CRCCalc(inputMessage))
        try:
            if msgcrc != codecrc:
                raise Exception("CRC mismatch")
            if accountId not in hass_platform.data[DOMAIN]:
                raise Exception("Not supported account " + accountId)
            response = hass_platform.data[DOMAIN][accountId].process_line(line)
        except Exception as e:
            _LOGGER.error(str(e))
            timestamp = datetime.fromtimestamp(time.time()).strftime(
                "_%H:%M:%S,%m-%d-%Y"
            )
            response = '"NAK"0000L0R0A0[]' + timestamp

        header = ("%04x" % len(response)).upper()
        CRC = AlarmTCPHandler.CRCCalc2(response)
        response = "\n" + CRC + header + response + "\r"

        byte_response = str.encode(response)
        self.request.sendall(byte_response)

    def handle(self):
        line = b""
        try:
            while True:
                raw = self.request.recv(1024)
                if (not raw) or (len(raw) == 0):
                    return
                raw = bytearray(raw)
                while True:
                    splitter = raw.find(b"\r")
                    if splitter > -1:
                        line = raw[1:splitter]
                        raw = raw[splitter + 1 :]
                    else:
                        break

                    self.handle_line(line)
        except Exception as e:
            _LOGGER.error(str(e) + " last line: " + line.decode())
            return

    @staticmethod
    def CRCCalc(msg):
        CRC = 0
        for letter in msg:
            temp = letter
            for _ in range(0, 8):
                temp ^= CRC & 1
                CRC >>= 1
                if (temp & 1) != 0:
                    CRC ^= 0xA001
                temp >>= 1

        return ("%x" % CRC).upper().zfill(4)

    @staticmethod
    def CRCCalc2(msg):
        CRC = 0
        for letter in msg:
            temp = ord(letter)
            for _ in range(0, 8):
                temp ^= CRC & 1
                CRC >>= 1
                if (temp & 1) != 0:
                    CRC ^= 0xA001
                temp >>= 1

        return ("%x" % CRC).upper().zfill(4)
