# XEZ 4008 emulator and gateway to MQTT broker

This python application opens a RS485 serial device and emulates a XEZ
4008 device and subscribes to a MQTT broker for topics `amt/{1,48}`
and publishes it as open or closed to a AMT 4010 alarm central from
Intelbras.

# XEZ 4008 and AMT 4010

The AMT 4010 is a alarm central from Intelbras which communicates with
expansion devices to connect additional PGMs, additional PIR motion
sensors,  wireless sensors and remote controls.

One of these expansion devices is the XEZ 4008, which connects to 8
wired PIR motion sensors and advertises them in the AMT 4010 alarm
central.

The communication is done through, what Intelbras calls, a A-B
bus. Which is a RS485 with 4800 8N1 configuration in a protocol that
resembles somewhat MODBUS RTU packets.

# Getting started

Clone the repository to a Linux machine with a RS485 adapter. Create a virtualenv:

```shell
$ virtualenv venv
```

Install dependencies:

```shell
$ source ./venv/bin/activate
$ pip install crcengine
$ pip install pyserial
$ pip install paho-mqtt
```

And then you can run it:

```shell
$ python -m xez-4008 -p 1883 --host mqtt-broker.com --address 1,2,3 -d /dev/ttyUSB0
```

Make sure you have permission to open your serial device and that it is configured for low_latency with setserial package:

```shell
$ sudo setserial /dev/ttyUSB0 low_latency
```

# Low latency

Use of `low_latency` is required for this program to work correctly,
because the MODBUS-like protocol uses timing for synchronization of
packet begin and end. Otherwise it may concatenate packets and discard
them because CRC doesn't match.

# Protocol

Protocol is simple and resembles MODBUS RTU. It starts with a byte
address, for example `0x0d` for XEZ configured in address 1.

It uses a CRC with the following specifications:

```
width=8 (1 byte)  poly=0x01  init=0xff  refin=false  refout=false  xorout=0x00  check=0xce  residue=0x00  name=(none)
```

The CRC is the last byte of every packet and for calculation purposes it must be filled with zero.

# Home Assistant

If you want to configure this for HomeAssistant, you must first
configure HomeAssistant to use the same MQTT Broker, and you can use a
MQTT switch by adding something like the following to `configuration.yaml`.

```
switch:
 - platform: mqtt
   name: "Virtual sensor 1"
   command_topic: "amt/25"
   payload_on: "on"
   payload_off: "off"
   qos: 1
   retain: true
```

There's no support for discovery yet.


