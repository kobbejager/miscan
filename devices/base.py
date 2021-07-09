#!/usr/bin/env python
from .xiaomi import Xiaomi
from .atc import Atc

class Device:

    def parse(self, mac, data):
        data = bytes.fromhex(data)

        if data[0:2] == b'\x95\xfe':
            return Xiaomi().parse(data)

        elif data[0:2] == b'\x1a\x18':
            return Atc().parse(data)

        else:
            return None