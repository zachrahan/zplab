# Copyright 2014 WUSTL ZPLAB
# Erik Hvatum (ice.rikh@gmail.com)

from PyQt5 import QtCore
import serial
from acquisition.device import Device

class BrightfieldLed(Device):
    enabledChanged = QtCore.pyqtSignal(bool)
    powerChanged = QtCore.pyqtSignal(int)


    def __init__(self, parent=None, deviceName='Brightfield LED Driver Controller', serialPortDescriptor='/dev/ttyIOTool'):
        super().__init__(parent, deviceName)
        self._serialPort = serial.Serial(serialPortDescriptor, 9600, timeout=0.1)
        self._serialPort.write(b'\x80\xFF\n') # disable echo
        self._serialPort.read(2) # read back last echo
        self.enabled = False
        self.power = 255

    @QtCore.pyqtProperty(bool, notify=enabledChanged)
    def enabled(self):
        return self._enabled

    @enabled.setter
    def enabled(self, enabled):
        self._enabled = bool(enabled)
        if enabled:
            self._serialPort.write(b'sh E6\n')
        else:
            self._serialPort.write(b'sl E6\n')
        self.enabledChanged.emit(self._enabled)

    @QtCore.pyqtProperty(int, notify=powerChanged)
    def power(self):
        return self._power

    @power.setter
    def power(self, power):
        assert 0 <= power <= 255
        self._power = int(power)
        self._serialPort.write(bytes('pm D7 {:d}'.format(power), encoding='ascii'))
        self.powerChanged.emit(self._power)
