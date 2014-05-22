# Copyright 2014 WUSTL ZPLAB
# Erik Hvatum (ice.rikh@gmail.com)

from PyQt5 import QtCore, QtGui, QtWidgets, QtOpenGL, QtSerialPort
import re
from acquisition.device import Device, DeviceException

class Dm6000b(Device):
    def __init__(self, serialPortDescriptor='/dev/ttyScope', name='Leica DM6000B'):
        super().__init__(name)
        self._appendTypeName('Dm6000b')

        # Note: QSerialPortInfo, which handles locating the serial port device from a serial port descriptor string, prepends
        # "/dev/" to the descriptor string.  PySerial does not do this, so we generally use 
        self._serialPort = serial.Serial(serialPortDescriptor, 19200, timeout=1)
        if not self._serialPort.isOpen():
            raise DeviceException(self, 'Failed to open {}.'.format(serialPortDescriptor))
