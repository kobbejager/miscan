#!/usr/bin/env python
import argparse
import os
import sys
from bluepy import btle

if os.getenv('C', '1') == '0':
    ANSI_RED = ''
    ANSI_GREEN = ''
    ANSI_YELLOW = ''
    ANSI_CYAN = ''
    ANSI_WHITE = ''
    ANSI_OFF = ''
else:
    ANSI_CSI = "\033["
    ANSI_RED = ANSI_CSI + '31m'
    ANSI_GREEN = ANSI_CSI + '32m'
    ANSI_YELLOW = ANSI_CSI + '33m'
    ANSI_CYAN = ANSI_CSI + '36m'
    ANSI_WHITE = ANSI_CSI + '37m'
    ANSI_OFF = ANSI_CSI + '0m'


class ScanDelegate(btle.DefaultDelegate):

    def __init__(self, opts):
        btle.DefaultDelegate.__init__(self)
        self.opts = opts

    def handleDiscovery(self, dev, isNewDev, isNewData):
        if isNewDev:
            status = "new"
        elif isNewData:
            if self.opts.new:
                return
            status = "update"
        else:
            if not self.opts.all:
                return
            status = "old"

        if dev.addr.startswith("a4:c1:38:") or dev.addr.startswith("58:2d:34:"):
            print ('    Device (%s): %s (%s), %d dBm %s' %
                (status,
                    ANSI_WHITE + dev.addr + ANSI_OFF,
                    dev.addrType,
                    dev.rssi,
                    ('' if dev.connectable else '(not connectable)'))
                )
            for (sdid, desc, val) in dev.getScanData():
                if sdid in [0x8, 0x9]:
                    print ('\t' + desc + ': \'' + ANSI_CYAN + val + ANSI_OFF + '\'')               
                if sdid in [0x16]:
                    print ('\t' + desc + ': \'' + ANSI_CYAN + val + ANSI_OFF + '\'')
                    parsed = parse(dev.addr, val)
                    if 'format' in parsed:
                        print ('\t    - format: ' + ANSI_YELLOW + parsed['format'] + ANSI_OFF)
                    if 'temperature' in parsed:
                        print ('\t    - temperature: ' + ANSI_YELLOW + str(parsed['temperature']) + ANSI_OFF + ' °C')
                    if 'humidity' in parsed:
                        print ('\t    - humidity: ' + ANSI_YELLOW + str(parsed['humidity']) + ANSI_OFF + ' %RH')
                    if 'battery' in parsed:
                        print ('\t    - battery: ' + ANSI_YELLOW + str(parsed['battery']) + ANSI_OFF + ' %')
            if not dev.scanData:
                print ('\t(no data)')
            print


def parse(mac, data):
    data = bytes.fromhex(data)

    message = dict()

    # Mijia BLE Broadcasting Protocol
    # https://github.com/pvvx/ATC_MiThermometer/blob/master/InfoMijiaBLE/Mijia%20BLE%20Broadcasting%20Protocol-Mi%20Beacon%20v4.md
    if data[0:2] == b'\x95\xfe':

        def from_word(b):
            return int.from_bytes(b, byteorder='little', signed=True) / 10

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

    # ATC
    # atc1441: https://github.com/atc1441/ATC_MiThermometer#advertising-format-of-the-custom-firmware
    # pvvx: https://github.com/pvvx/ATC_MiThermometer#technical-specifications
    if data[0:2] == b'\x1a\x18':
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



def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--hci', action='store', type=int, default=0,
                        help='Interface number for scan')
    parser.add_argument('-t', '--timeout', action='store', type=int, default=0,
                        help='Scan delay, 0 for continuous (=default)')
    parser.add_argument('-a', '--all', action='store_true',
                        help='Display duplicate adv responses, by default show new + updated')
    parser.add_argument('-n', '--new', action='store_true',
                        help='Display only new adv responses, by default show new + updated')
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='Increase output verbosity')
    arg = parser.parse_args(sys.argv[1:])

    btle.Debugging = arg.verbose

    scanner = btle.Scanner(arg.hci).withDelegate(ScanDelegate(arg))

    print ("Scanning...")
    scanner.scan(arg.timeout)


if __name__ == "__main__":
    main()