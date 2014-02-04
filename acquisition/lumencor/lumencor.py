#!/usr/bin/env python3
#
# Copyright 2014 WUSTL ZPLAB
#

#TODO: abstract port write into function that verifies return represents expected byte count & throws if not

import serial
import time

class Lumencor:
    def __init__(self, serialPortDescriptor = '/dev/tty.usbserial-FTVI2WYU'):
        self._serialPort = serial.Serial(serialPortDescriptor, 9600, timeout=1)
        #TODO: check that port was opened successfully
        #RS232 Lumencor docs state: "The [following] two commands MUST be issued after every power cycle to properly configure controls for further commands."
        # "Set GPIO0-3 as open drain output"
        self._serialPort.write(bytearray.fromhex(u'57 02 FF 50'))
        # "Set GPI05-7 push-pull out, GPIO4 open drain out"
        self._serialPort.write(bytearray.fromhex(u'57 03 AB 50'))
        # The lumencor box replies with nonsense to the first get temperature request.  We issue a get temperature request and ignore the result so that the next
        # get temperature request returns useful data.
        self.getTemp()

    def getTemp(self):
        if self._serialPort.write(bytearray.fromhex(u'53 91 02 50')) == 4:
            r = self._serialPort.read(2)
            if len(r) == 2:
                return ((r[0] << 3) | (r[1] >> 5)) * 0.125

    def testGreen(self):
        print("temp before: ", self.getTemp())
        # enable only green
        self._serialPort.write(bytearray.fromhex(u'4F 7D 50'))
        # green DAC to full intensity
        self._serialPort.write(bytearray.fromhex(u'53 18 03 04 F0 00 50'))
        time.sleep(5)
        # green DAC to no intensity
        self._serialPort.write(bytearray.fromhex(u'53 18 03 04 FF F0 50'))
        # disable all
        self._serialPort.write(bytearray.fromhex(u'4F 7F 50'))
        print("temp after: ", self.getTemp())

if __name__ == '__main__':
    from lumencor import direct_manip
    direct_manip.show()

