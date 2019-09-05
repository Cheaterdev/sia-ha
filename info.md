[![hacs][hacsbadge]](hacs)

_Component to integrate with [SIA][sia], based on [CheaterDev's version][ch_sia]._

**This component will set up the following platforms.**

Platform | Description
-- | --
`binary_sensor` | Show something `True` or `False`.

## Features
- Fire/gas tracker
- Water leak tracker
- Alarm tracking
- Armed state tracking
- Partial armed state tracking
- AES-128 CBC encryption support

{% if not installed %}
## Installation

1. Click install.
1. Add `sia:` to your HA configuration.

{% endif %}
## Example configuration.yaml

```yaml
sia:
  port:  port
  hubs:
    - name: name
      account: account
      encryption_key: password
```

## Configuration options

Key | Type | Required | Description
-- | -- | -- | --
`port` | `int` | `True` | Port that SIA will listen on.
`hubs` | `list` | `True` | List of all hubs to connect to.
`name` | `string` | `True` | Used to generate sensor ids.
`account` | `string` | `True` |  Hub account to track. 3-16 ASCII hex characters. Must be same, as in hub properties.
`encryption_key` | `string` | `False` | Encoding key. 16 ASCII characters. Must be same, as in hub properties.

ASCII characters are 0-9 and ABCDEF, so a account is something like `346EB` and the encryption key is the same but 16 characters.


***

[sia]: https://github.com/eavanvalkenburg/sia-ha
[ch_sia]: https://github.com/Cheaterdev/sia-ha
[hacs]: https://github.com/custom-components/hacs
[hacsbadge]: https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge