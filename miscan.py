#!/usr/bin/env python
import argparse
import sys
import logging
import json
from datetime import datetime

from bluepy import btle
import paho.mqtt.client as mqtt
import pytz

from devices.base import Device


# Default settings
settings = {
    "mqtt" : {
        "client_id": "miscan",
        "host": "test.mosquitto.org",
        "port": 1883,
        "keepalive": 60,
        "bind_address": "",
        "username": None,
        "password": None,
        "qos": 0,
        "pub_topic_namespace": "miscan",
        "retain": False,
        "timezone": "UTC" # https://en.wikipedia.org/wiki/List_of_tz_database_time_zones
    },
    "ble": {
        "hci": 0,                # interface number to scan
        "timeout": 0,            # scan delay, 0=continuous
        "messages": "updated"    # show messages: new, updated, all
    },
    "devices": {
    }
}


class ScanDelegate(btle.DefaultDelegate):

    def __init__(self, which_messages):
        btle.DefaultDelegate.__init__(self)
        self.which_messages = which_messages

    def handleDiscovery(self, dev, isNewDev, isNewData):
        if isNewDev:
            status = "new"
        elif isNewData:
            if self.which_messages == "new":
                return
            status = "update"
        else:
            if self.which_messages != "all":
                return
            status = "old"

        if dev.addr.startswith("a4:c1:38:") or dev.addr.startswith("58:2d:34:"):
            for (sdid, desc, val) in dev.getScanData():
                if sdid in [0x8, 0x9]:
                    log.debug(f"Message from {dev.addr} ({dev.rssi} dBm): {desc}: {val}")               
                if sdid in [0x16]:
                    message = Device().parse(dev.addr, val)
                    if message: 
                        log.debug(f"Message from {dev.addr} ({dev.rssi} dBm): {message}")
                        message["address"] = dev.addr
                        message["rssi"] = dev.rssi
                        message["timestamp"] = datetime.now(pytz.timezone(settings['mqtt']['timezone'])).isoformat('T', 'seconds')
                        message["status"] = status
                        on_mi_message(message)
            if not dev.scanData:
                log.debug(f"Message from {dev.addr} ({dev.rssi} dBm): no data")


def on_mqtt_connect(client, userdata, flags, rc):
    # Send out a message telling we're online
    log.info(f"Connected to MQTT with result code {rc}")
    mqtt_client.publish(
        topic=settings['mqtt']['pub_topic_namespace'],
        payload="online",
        qos=settings['mqtt']['qos'],
        retain=True)


def on_mi_message(message):
    # Lookup device name
    if message['address'] in settings['devices']:
        device_name = settings['devices'][message['address']]
    else:
        device_name = message['address']

    # Send out messages to the MQTT broker
    mqtt_client.publish(
        topic=f"{settings['mqtt']['pub_topic_namespace']}/{device_name}",
        payload=json.dumps(message),
        qos=settings['mqtt']['qos'],
        retain=settings['mqtt']['retain'])

    subtopics = ['temperature', 'humidity', 'battery']
    for subtopic in subtopics:
        if subtopic in message:
            mqtt_client.publish(
                topic=f"{settings['mqtt']['pub_topic_namespace']}/{device_name}/{subtopic}",
                payload=message[subtopic],
                qos=settings['mqtt']['qos'],
                retain=settings['mqtt']['retain'])


# Parse arguments
parser = argparse.ArgumentParser(description="XIAOMI temperature/humidity sensor to MQTT bridge")
parser.add_argument("-c", "--config", default=None, 
                    help="Configuration file")
parser.add_argument("-l", "--loglevel", default="INFO", 
                    help="Event level to log (default: %(default)s)")
args = parser.parse_args()


# Set up logging
log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
num_level = getattr(logging, args.loglevel.upper(), None)
if not isinstance(num_level, int):
    raise ValueError('Invalid log level: %s' % args.loglevel)
logging.basicConfig(level=num_level, format=log_format)
log = logging.getLogger(__name__)
log.info('Loglevel is %s', logging.getLevelName(log.getEffectiveLevel()))


# Update default settings from the settings file
if args.config:
    with open(args.config) as f:
        overrides = json.load(f)
        if 'mqtt' in overrides and isinstance(overrides['mqtt'], dict):
            settings['mqtt'].update(overrides['mqtt'])
        if 'ble' in overrides and isinstance(overrides['ble'], dict):
            settings['ble'].update(overrides['ble'])
        if 'devices' in overrides and isinstance(overrides['devices'], dict):
            settings['devices'].update(overrides['devices'])


# Set up paho-mqtt
mqtt_client = mqtt.Client(
    client_id=settings['mqtt']['client_id'])
mqtt_client.on_connect = on_mqtt_connect

if settings['mqtt']['username']:
    mqtt_client.username_pw_set(
        settings['mqtt']['username'],
        settings['mqtt']['password'])

# The will makes sure the device registers as offline when the connection
# is lost
mqtt_client.will_set(
    topic=settings['mqtt']['pub_topic_namespace'],
    payload="offline",
    qos=settings['mqtt']['qos'],
    retain=True)

# Let's not wait for the connection, as it may not succeed if we're not
# connected to the network or anything. Such is the beauty of MQTT
mqtt_client.connect_async(
    host=settings['mqtt']['host'],
    port=settings['mqtt']['port'],
    keepalive=settings['mqtt']['keepalive'],
    bind_address=settings['mqtt']['bind_address'])
mqtt_client.loop_start()




def main():
    scanner = btle.Scanner(settings['ble']['hci']).withDelegate(ScanDelegate(settings['ble']['messages']))

    log.info("Scanning for devices...")
    scanner.scan(settings['ble']['timeout'], passive=True)


if __name__ == "__main__":
    main()
