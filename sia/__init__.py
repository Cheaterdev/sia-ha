import asyncio
import logging
import json
import voluptuous as vol
import sseclient
import requests
import time
from collections import defaultdict
from requests_toolbelt.utils import dump
from homeassistant.core import callback
import voluptuous as vol
from datetime import timedelta
from homeassistant.exceptions import TemplateError
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.entity import Entity, async_generate_entity_id
from homeassistant.helpers.event import async_track_state_change

from threading import Thread
from homeassistant.helpers import discovery
from homeassistant.components.binary_sensor import BinarySensorDevice
from homeassistant.helpers.restore_state import RestoreEntity
_LOGGER = logging.getLogger(__name__)
from homeassistant.const import (STATE_ON, STATE_OFF)

from homeassistant.const import (
    CONF_NAME, CONF_PORT, CONF_PASSWORD)
import socketserver 
from datetime import datetime
import time
import logging
import threading
import sys
import re

from Crypto.Cipher import AES
from binascii import unhexlify,hexlify
from Crypto import Random
import random, string, base64
from homeassistant.helpers.event import async_track_point_in_utc_time
from homeassistant.util.dt import utcnow

DOMAIN = 'sia'
CONF_HUBS = 'hubs'
CONF_ACCOUNT = 'account'

HUB_CONFIG = vol.Schema({
    vol.Required(CONF_NAME): cv.string,
    vol.Required(CONF_ACCOUNT): cv.string,
    vol.Optional(CONF_PASSWORD):cv.string,
})



CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
        vol.Required(CONF_PORT): cv.string,
        vol.Required(CONF_HUBS, default={}):
            vol.All(cv.ensure_list, [HUB_CONFIG]),
    }),
}, extra=vol.ALLOW_EXTRA)

ID_STRING = '"SIA-DCS"'.encode()
ID_STRING_ENCODED = '"*SIA-DCS"'.encode()

TIME_TILL_UNAVAILABLE = timedelta(minutes=3)

ID_R='\r'.encode()

hass_platform = None


def setup(hass, config):
    global hass_platform
    socketserver.TCPServer.allow_reuse_address = True
    hass_platform = hass

    hass_platform.data[DOMAIN] = {}

    port = int(config[DOMAIN][CONF_PORT])

    for hub_config in config[DOMAIN][CONF_HUBS]:
        if CONF_PASSWORD in hub_config:
            hass.data[DOMAIN][hub_config[CONF_ACCOUNT]] = EncriptedHub(hass, hub_config)
        else:
            hass.data[DOMAIN][hub_config[CONF_ACCOUNT]] = Hub(hass, hub_config)
          
    for component in ['binary_sensor']:
       discovery.load_platform(hass, component, DOMAIN, {}, config)

    server = socketserver.TCPServer(("", port), AlarmTCPHandler)

    t = threading.Thread(target=server.serve_forever)
    t.start()
    
    return True

class Hub:
    reactions = {            
            "BA" : [{"state":"ALARM","value":True}],
            "TA" : [{"state":"ALARM" ,"value":True}],
            "CL" : [{"state":"STATUS" ,"value":False},{"state":"STATUS_TEMP" ,"value":False}],
            "NL" : [{"state":"STATUS" ,"value":True},{"state":"STATUS_TEMP" ,"value":False}],
            "WA":  [{"state":"LEAK","value":True}],
            "WH":  [{"state":"LEAK" ,"value":False}],
            "GA":  [{"state":"GAS","value":True}],
            "GH":  [{"state":"GAS" ,"value":False}],
            "BR" : [{"state":"ALARM","value":False}],
            "OP" : [{"state":"STATUS","value":True},{"state":"STATUS_TEMP","value":True}],
            "RP" : []
        }

    def __init__(self, hass, hub_config):
        self._name = hub_config[CONF_NAME]
        self._accountId = hub_config[CONF_ACCOUNT]
        self._hass = hass
        self._states = {}
        self._states["LEAK"] = SIABinarySensor("sia_leak_" + self._name,"moisture" , hass)
        self._states["GAS"] = SIABinarySensor("sia_gas_" + self._name,"smoke", hass)
        self._states["ALARM"]  = SIABinarySensor("sia_alarm_" + self._name,"safety", hass)
        self._states["STATUS"]  = SIABinarySensor("sia_status_" + self._name, "lock", hass)
        self._states["STATUS_TEMP"]  = SIABinarySensor("sia_status_temporal_" + self._name, "lock", hass)
    
    def manage_string(self, msg):
       # _LOGGER.error("manage_string: " + msg )
        tipo = msg[msg.index('/')+1:msg.index('/')+3]

        if tipo in self.reactions:
            reactions = self.reactions[tipo]
            for reaction in reactions:
                state = reaction["state"]
                value = reaction["value"]
                #_LOGGER.error("manageAlarmMessage: " + DOMAIN + " " + self._name + " " + state )
                
                self._states[state].new_state(value)
        else:
            _LOGGER.error("unknown event: " + tipo )
        
        for device in self._states:
           self._states[device].assume_available()



    def process_line(self, line):
        pos = line.find(ID_STRING)
        seq = line[pos+len(ID_STRING) : pos+len(ID_STRING)+4]
        data = line[line.index(b'[') :]
        self.manage_string(data.decode())
        return '"ACK"'  + (seq.decode()) + 'L0#' + (self._accountId) + '[]'
        

class EncriptedHub(Hub):
    def __init__(self, hass, hub_config):
        self._key = hub_config[CONF_PASSWORD].encode("utf8")
        iv = unhexlify("00000000000000000000000000000000")  #other vector produces invalid data at beginning
        _cipher = AES.new(self._key, AES.MODE_CBC, iv)
        self._ending = hexlify(_cipher.encrypt( "00000000000000|]".encode("utf8") )).decode(encoding='UTF-8').upper()
        Hub.__init__(self, hass, hub_config)

    def manage_string(self, msg):
       # _LOGGER.error("manage_string orig: " + msg[1:] )
        iv = unhexlify("00000000000000000000000000000000")  #other vector produces invalid data at beginning
        _cipher = AES.new(self._key, AES.MODE_CBC, iv)
        data = _cipher.decrypt(unhexlify(msg[1:]))
      #  _LOGGER.error("manage_string res: " + data.decode(encoding='UTF-8',errors='replace') )
    
        data = data[data.index(b'|'):]
        resmsg = data.decode(encoding='UTF-8',errors='replace')
               
        Hub.manage_string(self, resmsg)

    def process_line(self, line):
        pos = line.find(ID_STRING_ENCODED)
        seq = line[pos+len(ID_STRING_ENCODED) : pos+len(ID_STRING_ENCODED)+4]
        data = line[line.index(b'[') :]
        self.manage_string(data.decode())
        return '"*ACK"'  + (seq.decode()) + 'L0#' + (self._accountId) + '[' + self._ending
  
        

class SIABinarySensor( RestoreEntity):
    def __init__(self,  name, device_class, hass):
        self._device_class = device_class
        self._should_poll = False
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
        """Return the name of the device."""
        return self._name

    @property
    def state(self):
        """Return the state of the binary sensor."""
        return STATE_ON if self.is_on else STATE_OFF

    @property
    def unique_id(self) -> str:
        """Return a unique ID."""
        return self._name

    @property
    def available(self):
        """Return True if entity is available."""
        return self._is_available

    @property
    def device_state_attributes(self):
        """Return the state attributes."""
        attrs = {}
        return attrs

    @property
    def device_class(self):
        return self._device_class

    @property
    def is_on(self):
        return self._state

    def new_state(self, state):   
        self._state = state
        self.async_schedule_update_ha_state()

    def assume_available(self):
        self._async_track_unavailable()

    @callback
    def _async_track_unavailable(self):
        if self._remove_unavailability_tracker:
            self._remove_unavailability_tracker()
        self._remove_unavailability_tracker = async_track_point_in_utc_time(
            self.hass, self._async_set_unavailable,
            utcnow() + TIME_TILL_UNAVAILABLE)
        if not self._is_available:
            self._is_available = True
            return True
        return False

    @callback
    def _async_set_unavailable(self, now):
        """Set state to UNAVAILABLE."""
        self._remove_unavailability_tracker = None
        self._is_available = False
        self.async_schedule_update_ha_state()

class AlarmTCPHandler(socketserver.BaseRequestHandler):
    _received_data = "".encode()

    def handle_line(self, line):
       # _LOGGER.error("handle_line: " + line.decode() )
        accountId = line[line.index(b'#') +1: line.index(b'[')].decode()

        pos = line.find(b'"')
        inputMessage=line[pos:]
        msgcrc = line[0:4] 
        codecrc = str.encode(AlarmTCPHandler.CRCCalc(inputMessage))

        try:
            if msgcrc != codecrc:
                raise Exception('CRC mismatch')
            
            if(accountId not in hass_platform.data[DOMAIN]):
                raise Exception('Not supported account ' + accountId)
            response = hass_platform.data[DOMAIN][accountId].process_line(line)
        except Exception as e:
            _LOGGER.error(str(e))
            timestamp = datetime.fromtimestamp(time.time()).strftime('_%H:%M:%S,%m-%d-%Y')
            response = '"NAK"0000L0R0A0[]' + timestamp

        header = ('%04x' % len(response)).upper()
        CRC = AlarmTCPHandler.CRCCalc2(response)
        response="\n" + CRC + header + response + "\r"

        byte_response = str.encode(response)
        self.request.sendall(byte_response)


    def handle(self):
        try:
            while True:
                raw = self.request.recv(1024)
                if (not raw) or (len(raw) == 0):
                    return
                raw = bytearray(raw)
                while True:
                    splitter = raw.find(b'\r')
                    if splitter> -1:
                        line = raw[1:splitter]
                        raw = raw[splitter+1:]
                    else:
                        break
                    
                    self.handle_line(line)
        except Exception as e: 
            _LOGGER.error("SIA error: " + str(e))
            return

    @staticmethod
    def CRCCalc(msg):
        CRC=0
        for letter in msg:
            temp=(letter)
            for j in range(0,8):  # @UnusedVariable
                temp ^= CRC & 1
                CRC >>= 1
                if (temp & 1) != 0:
                    CRC ^= 0xA001
                temp >>= 1
                
        return ('%x' % CRC).upper().zfill(4)
    
    @staticmethod
    def CRCCalc2(msg):
        CRC=0
        for letter in msg:
            temp=ord(letter)
            for j in range(0,8):  # @UnusedVariable
                temp ^= CRC & 1
                CRC >>= 1
                if (temp & 1) != 0:
                    CRC ^= 0xA001
                temp >>= 1
                
        return ('%x' % CRC).upper().zfill(4)