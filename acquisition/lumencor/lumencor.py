# Copyright 2014 WUSTL ZPLAB

from numpy import *
import serial
import time
from acquisition.lumencor.lumencor_exception import LumencorException

class Lumencor:
    _colorToggleLeftShiftIndexes = {
        'red'   : 0,
        'green' : 1,
        'cyan'  : 2,
        'UV'    : 3,
        'blue'  : 5,
        'teal'  : 6 }
    _colorIntensityBases = {
        'red'   : bytearray.fromhex('53 18 03 08 F0 00 50'),
        'green' : bytearray.fromhex('53 18 03 04 F0 00 50'),
        'cyan'  : bytearray.fromhex('53 18 03 02 F0 00 50'),
        'UV'    : bytearray.fromhex('53 18 03 01 F0 00 50'),
        'blue'  : bytearray.fromhex('53 1A 03 01 F0 00 50'),
        'teal'  : bytearray.fromhex('53 1A 03 02 F0 00 50') }

    def __init__(self, serialPortDescriptor = '/dev/tty.usbserial-FTVI2WYU'):
        self._serialPort = serial.Serial(serialPortDescriptor, 9600, timeout=1)
        #TODO: check that port was opened successfully
        #RS232 Lumencor docs state: "The [following] two commands MUST be issued after every power cycle to properly configure controls for further commands."
        # "Set GPIO0-3 as open drain output"
        self._write(bytearray.fromhex(u'57 02 FF 50'))
        # "Set GPI05-7 push-pull out, GPIO4 open drain out"
        self._write(bytearray.fromhex(u'57 03 AB 50'))
        # The lumencor box replies with nonsense to the first get temperature request.  We issue a get temperature request and ignore the result so that the next
        # get temperature request returns useful data.
        self.getTemp()
        self.toggleAllColors(True)
        self.setAllColorsIntensity(0)

    def _write(self, byteArray):
        #print(''.join('{:02x} '.format(x) for x in byteArray))
        byteCountWritten = self._serialPort.write(byteArray)
        byteCount = len(byteArray)
        if byteCountWritten != byteCount:
            raise LumencorException('Attempted to write {} bytes to Lumencor serial port, but only {} bytes were written.'.format(byteCount, byteCountWritten))

    def getTemp(self):
        self._write(bytearray.fromhex(u'53 91 02 50'))
        r = self._serialPort.read(2)
        if len(r) == 2:
            return ((r[0] << 3) | (r[1] >> 5)) * 0.125

    def toggleAllColors(self, on):
        self._colors = bytearray.fromhex('4f 00 50')
        if not on:
            self._colors[1] = 0x7f
        self._write(self._colors)

    def toggleColor(self, color, on):
        shifted = 1 << Lumencor._colorToggleLeftShiftIndexes[color]
        if not on:
            self._colors[1] |= shifted
        else:
            self._colors[1] &= 0x7f ^ shifted
        self._write(self._colors)

    def _applyIntensity(self, byteArray, intensity):
        if intensity < 0 or intensity > 0xff:
            raise ValueError('intensity < 0 or intensity > 0xff')
        intensity = 0xff - intensity
        byteArray[4] |= (intensity & 0xf0) >> 4
        byteArray[5] |= (intensity & 0x0f) << 4

    def setAllColorsIntensity(self, intensity):
        # red, green, cyan, UV
        o = bytearray.fromhex('53 18 03 0F F0 00 50')
        self._applyIntensity(o, intensity)
        self._write(o)
        # teal, blue
        o = bytearray.fromhex('53 1A 03 03 F0 00 50')
        self._applyIntensity(o, intensity)
        self._write(o)

    def setColorIntensity(self, color, intensity):
        o = Lumencor._colorIntensityBases[color].copy()
        self._applyIntensity(o, intensity)
        self._write(o)

