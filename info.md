[![hacs][hacsbadge]](hacs)

_Component to integrate with [SIA][sia], based on [CheaterDev's version][ch_sia]._

**This component will set up the following platforms.**

## WARNING
This integration may be unsecure. You can use it, but it's at your own risk.
This integration was tested with Ajax Systems security hub only. Other SIA hubs may not work.

Platform | Description
-- | --
`binary_sensor` | A smoke or moisture sensor.
`alarm_control_panel` | Alarm panel with the state of the alarm.
`sensor` | Sensor with the last heartbeat message from your system.

## Features
- Alarm tracking with a alarm_control_panel component
- Optional Fire/gas tracker
- Optional Water leak tracker
- AES-128 CBC encryption support

## Hub Setup(Ajax Systems Hub example)

1. Select "SIA Protocol". 
2. Enable "Connect on demand". 
3. Place Account Id - 3-16 ASCII hex characters. For example AAA.
4. Insert Home Assistant IP adress. It must be visible to hub. There is no cloud connection to it.
5. Insert Home Assistant listening port. This port must not be used with anything else.
6. Select Preferred Network. Ethernet is preferred if hub and HA in same network. Multiple networks are not tested.
7. Enable Periodic Reports. It must be smaller than 5 mins. If more - HA will mark hub as unavailable.
8. Encryption is on your risk. There is no CPU or network hit, so it's preferred. Password is 16 ASCII characters.
{% if not installed %}
## Installation

1. Click install.
1. Add at least the minimum configuration to your HA configuration, see below.

### Minimum config
This is the least amount of information that needs to be in your config. This will result in a `sensor.hubname_last_heartbeat` being added after reboot. Dynamically any other sensors are added.

```yaml
sia:
  port:  port
  hubs:
    - name: hubname
      account: account
```

{% endif %}
## Full configuration

```yaml
sia:
  port:  port
  hubs:
    - name: hubname
      account: account
      encryption_key: password
      zones:
        - zone: 1
          name: zonename
          sensors:
           - alarm
           - moisture
           - smoke
```

## Configuration options

Key | Type | Required | Description
-- | -- | -- | --
`port` | `int` | `True` | Port that SIA will listen on.
`hubs` | `list` | `True` | List of all hubs to connect to.
`name` | `string` | `True` | Used to generate sensor ids.
`account` | `string` | `True` |  Hub account to track. 3-16 ASCII hex characters. Must be same, as in hub properties.
`encryption_key` | `string` | `False` | Encoding key. 16 ASCII characters. Must be same, as in hub properties.
`zones` | `list` | `False` | Manual definition of all zones present, if unspecified, only the hub sensor is added, and new sensors are added based on messages coming in.
`zone` | `int` | `False` | ZoneID, must match the zone that the system sends, can be found in the log but also "discovered"
`name` | `string` | `False` | Zone name, is used for the friendly name of your sensors, when you have the same sensortypes in multiple zones and this is not set, a `_1, _2, etc` is added by HA automatically.
`sensors` | `list` | `False` | a list of sensors, must be of type: `alarm`, `moisture` (HA standard name for a leak sensor) or `smoke`

ASCII characters are 0-9 and ABCDEF, so a account is something like `346EB` and the encryption key is the same but 16 characters.
***

[sia]: https://github.com/eavanvalkenburg/sia-ha
[ch_sia]: https://github.com/Cheaterdev/sia-ha
[hacs]: https://github.com/custom-components/hacs
[hacsbadge]: https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge