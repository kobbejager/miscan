#!/usr/bin/env python
import argparse
import sys
from bluepy import btle

from devices.base import Device

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
                    dev.addr,
                    dev.addrType,
                    dev.rssi,
                    ('' if dev.connectable else '(not connectable)'))
                )
            for (sdid, desc, val) in dev.getScanData():
                if sdid in [0x8, 0x9]:
                    print ('\t' + desc + ': \'' + val + '\'')               
                if sdid in [0x16]:
                    print ('\t' + desc + ': \''  + val + '\'')
                    parsed = Device().parse(dev.addr, val)
                    if 'format' in parsed:
                        print ('\t    - format: ' + parsed['format'])
                    if 'temperature' in parsed:
                        print ('\t    - temperature: ' + str(parsed['temperature']) + ' °C')
                    if 'humidity' in parsed:
                        print ('\t    - humidity: ' + str(parsed['humidity']) + ' %RH')
                    if 'battery' in parsed:
                        print ('\t    - battery: ' + str(parsed['battery']) + ' %')
            if not dev.scanData:
                print ('\t(no data)')
            print


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
