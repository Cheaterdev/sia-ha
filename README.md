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

## Hub Setup(Ajax Systems Hub example)

1. Select "SIA Protocol". 
2. Enable "Connect on demand". 
3. Place Account Id - 3-16 ASCII hex characters. For example AAA.
4. Insert Home Assistant IP adress. It must be visible to hub. There is no cloud connection to it.
5. Insert Home Assistant listening port. This port must not be used with anything else.
6. Select Preferred Network. Ethernet is preferred if hub and HA in same network. Multiple networks are not tested.
7. Enable Periodic Reports. It must be smaller than 5 mins. If more - HA will mark hub as unavailable.
8. Encryption is on your risk. There is no CPU or network hit, so it's preferred. Password is 16 ASCII characters.
    

## Home Assistant Setup

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
- **password** (*Optional*): Encoding key. 16 ASCII characters. Must be same, as in hub properties.

## Disclaimer
This software is supplied "AS IS" without any warranties and support.

