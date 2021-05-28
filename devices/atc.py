#!/usr/bin/env python

# ATC
# atc1441: https://github.com/atc1441/ATC_MiThermometer#advertising-format-of-the-custom-firmware
# pvvx: https://github.com/pvvx/ATC_MiThermometer#technical-specifications

class Atc:

    def parse(self, data):
        message = dict()

        if len(data) == 17:
            message['format'] = 'ATC/PVVX'
            message['temperature'] = int.from_bytes(data[8:10], byteorder='little', signed=True) / 100
            message['humidity'] = int.from_bytes(data[10:12], byteorder='little') / 100
            message['battery'] = data[14]

        elif len(data) == 15:
            message['format'] = 'ATC1441'
            message['temperature'] = int.from_bytes(data[8:10], byteorder='big', signed=True) / 10
            message['humidity'] = data[10]
            message['battery'] = data[11]

        return message