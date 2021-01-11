[![hacs][hacsbadge]](hacs)

_Component to integrate with [SIA], based on [CheaterDev's version][ch_sia]._

_Latest beta will be suggested for inclusion as a official integration._

**This component will set up the following platforms.**

## WARNING
This integration may be unsecure. You can use it, but it's at your own risk.
This integration was tested with Ajax Systems security hub only. Other SIA hubs may not work.

Platform | Description
-- | --
`binary_sensor` | A smoke and moisture sensor, one of each per account and zone. Power sensor for the hub. You can disable these sensors if you do not have those devices.
`alarm_control_panel` | Alarm panel with the state of the alarm, one per account and zone. You can disable this sensor if you have zones defined with just sensors and no alarm.
`sensor` | Sensor with the last heartbeat message from your system, one  per account. Please do not disable this sensor as it will show you the status of the connection.

## Features
- Alarm tracking with a alarm_control_panel component, but no alarm setting
- Fire/gas tracker
- Water leak tracker
- Hub Power status tracker
- AES-128 CBC encryption support

## Hub Setup (Ajax Systems Hub example)

1. Select "SIA Protocol". 
2. Enable "Connect on demand". 
3. Place Account Id - 3-16 ASCII hex characters. For example AAA.
4. Insert Home Assistant IP address. It must be a visible to hub. There is no cloud connection to it.
5. Insert Home Assistant listening port. This port must not be used with anything else.
6. Select Preferred Network. Ethernet is preferred if hub and HA in same network. Multiple networks are not tested.
7. Enable Periodic Reports. The interval with which the alarm systems reports to the monitoring station, default is 1 minute. This component adds 30 seconds before setting the alarm unavailable to deal with slights latencies between ajax and HA and the async nature of HA.
8. Encryption is on your risk. There is no CPU or network hit, so it's preferred. Password is 16 ASCII characters.

## Installation

1. Click install.
1. The latest version is only available through a config flow.
1. After clicking the add button in the Integration pane, you full in the below fields.

If you have multiple accounts that you want to monitor you can choose to have both communicating with the same port, in that case, use the additional accounts checkbox in the config so setup the second (and more) accounts. You can also choose to have both running on a different port, in that case setup the component twice.

After setup you will see one entity per account for the heartbeat, and 3 entities for each zone per account, alarm, smoke sensor and moisture sensor. This means at least four entities are added, each will also have a device associated with it, so allow you to use the area feature. Unwanted sensors should be hidden in the interface.

## Configuration options

Key | Type | Required | Description
-- | -- | -- | --
`port` | `int` | `True` | Port that SIA will listen on.
`account` | `string` | `True` |  Hub account to track. 3-16 ASCII hex characters. Must be same, as in hub properties.
`encryption_key` | `string` | `False` | Encoding key. 16 ASCII characters. Must be same, as in hub properties.
`ping_interval` | `int` | `True` | Ping interval in minutes that the alarm system uses to send "Automatic communication test report" messages, the HA component adds 30 seconds before marking a device unavailable. Must be between 1 and 1440 minutes, default is 1.
`zones` | `int` | `True` | The number of zones present for the account, default is 1.
`additional_account` | `bool` | `True` | Used to ask for additional accounts in multiple steps during setup, default is False.

ASCII characters are 0-9 and ABCDEF, so a account is something like `346EB` and the encryption key is the same but 16 characters.
***

## Debugging
To turn on debugging go into your `configuration.yaml` and add these lines:
```yaml
logger:
  default: error
  logs:
    custom_components.sia: debug 
    pysiaalarm: debug
```

[SIA]: https://github.com/eavanvalkenburg/sia-ha
[ch_sia]: https://github.com/Cheaterdev/sia-ha
[hacs]: https://github.com/custom-components/hacs
[hacsbadge]: https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge
