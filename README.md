# sia-ha
SIA alarm systems integration into Home Assistant
Based on https://github.com/bitblaster/alarmreceiver

## WARNING
This integration may be unsecure. You can use it, but it's at your own risk.
This integration was tested with Ajax Systems security hub only. Other SIA hubs may not work.

## Features
- Fire/gas tracker
- Water leak tracker
- Alarm tracking
- Armed state tracking
- Partial armed state tracking
- AES-128 CBC encryption support

## Setup

Place "sia" folder in **/custom_components** folder
	
```yaml
# configuration.yaml
    
sia:
  port:  **port**
  hubs:
    - name: **name**
      account: **account**
      password: *password*
  
```

Configuration variables:
- **port** (*Required*): Listeting port
- **hubs** (*Required*): List of hubs
- **name** (*Required*): Used to generate sensor ids.
- **account** (*Required*): Hub account to track. 3-16 ASCII hex characters. Must be same, as in hub properties.
- **password** (*Optional*): Encoding key. 16 symbols. Must be same, as in hub properties.

## Disclaimer
This software is supplied "AS IS" without any warranties and support.

