
import argparse
import protocol
import paho.mqtt.client as mqtt
import sensors
import sys
from queue import Queue

parser = argparse.ArgumentParser(description='XEZ 4008 emulator for AMT 4010 smart alarm using RS485 and MQTT.')
parser.add_argument('--host', help='Host of MQTT broker to subscribe', required=True)
parser.add_argument('-p', '--port', help='Port of MQTT broker to subscribe', type=int, default=1883)
parser.add_argument('-a', '--address', help='Address of XEZ', default=1883, required=True)
parser.add_argument('-d', '--device', help='Serial device (e.g. ttyUSB0)', required=True)

args = parser.parse_args()

addresses = args.address.split(',')
addresses = [int(i) for i in addresses]

print ('XEZ Addresses', addresses, file=sys.stderr)

sensors = sensors.Sensors (addresses)

p = protocol.create (args.device)

queue = Queue()

def mqtt_on_connect (client, userdata, flags, rc):
    if rc==0:
        print ("Connected to MQTT broker", file=sys.stderr)
        client.subscribe("amt/#")
    else:
        print ("Error trying to connect to MQTT broker", file=sys.stderr)

def mqtt_on_message (client, userdata, msg):
    queue.put (msg)

client = mqtt.Client()
client.on_connect = mqtt_on_connect
client.on_message = mqtt_on_message

client.reconnect_delay_set(min_delay=1, max_delay=120)
client.loop_start ()
client.connect_async (args.host, args.port)

print ("Started XEZ 4008 emulation loop", file=sys.stderr)

run = True
while run:
    def handle_msg (msg):
        address = msg[0]
        if address >= 0x0d and address < (0x0d + 6):
            expander = (address - 0x0d) + 1
            expanders = sensors.expanders()
            if expander in expanders:
                #print ('expander ', expander, 'is in expanders msg is ', msg)
                if msg[1] == 0x20 and len(msg) == 8:
                    sensors_byte = 0xff
                    sensors_state = sensors.get_sensors_from_expander(expander)
                    #print ('sensors state', sensors_state)
                    for i in range (8):
                        if not sensors_state[i]:
                            sensors_byte = sensors_byte & ~(1 << i)
                    data = bytes([address]) + b'\x03' + bytes([sensors_byte]) + b'\x00\x00'
                    #print ('sending sensor data: ', sensors_byte, ' for address ', address, ' packet ', data)
                    p.send (data)
                elif msg[1] == 0x24 and len(msg) == 4:
                    config_byte = msg[3]
                    p.send (bytes([address]) + b'\x01' + bytes([config_byte]))
                elif msg[1] == 0x23 and len(msg) == 3:
                    p.send (bytes([address]) + b'\x02\x00\x00')

    while not queue.empty():
        try:
            msg = queue.get()
            print (msg.topic + " " + str(msg.payload), file=sys.stderr)
            if msg.topic[:4] == 'amt/':
                sensor = int (msg.topic[4:])
                if msg.payload == b'on':
                    sensors.sensor_on (sensor)
                else:
                    sensors.sensor_off (sensor)
        except ValueError:
            pass

    p.loop (handle_msg)

client.loop_stop()
