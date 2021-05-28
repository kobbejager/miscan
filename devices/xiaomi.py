#!/usr/bin/env python

# Mijia BLE Broadcasting Protocol
# https://github.com/pvvx/ATC_MiThermometer/blob/master/InfoMijiaBLE/Mijia%20BLE%20Broadcasting%20Protocol-Mi%20Beacon%20v4.md


class Xiaomi:

    def parse(self, data):
        message = dict()
        message['format'] = 'XIAOMI'

        typ = data[13]
        if typ == 0x04:  # temperature
            message['temperature'] = from_word(data[16:18])
        if typ == 0x06:  # humidity
            message['humidity'] = from_word(data[16:18])
        if typ == 0x0a:  # battery
            message['battery'] = data[16]
        if typ == 0x0d:  # humidity + temperature
            message['temperature'] = from_word(data[16:18])
            message['humidity'] = from_word(data[18:20])

        return message


def from_word(b):
    return int.from_bytes(b, byteorder='little', signed=True) / 10
