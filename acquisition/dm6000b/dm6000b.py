# Copyright 2014 WUSTL ZPLAB
# Erik Hvatum (ice.rikh@gmail.com)

from PyQt5 import QtCore, QtSerialPort
import re
from acquisition.device import Device, DeviceException

class Dm6000b(Device):
    def __init__(self, parent=None, deviceName='Leica DM6000B', serialPortDescriptor='/dev/ttyScope'):
        super().__init__(parent, deviceName)

        # Note: QSerialPortInfo, which handles locating the serial port device from a serial port descriptor string, prepends
        # "/dev/" to the descriptor string.  PySerial does not do this, so we generally use full paths which include the /dev/
        # part and chop off the /dev/ when passing to QSerialPort classes.
        match = re.match(r'/dev/([^/]+)', serialPortDescriptor)
        if match:
            serialPortDescriptor_ = match.group(1)
        else:
            serialPortDescriptor_ = serialPortDescriptor
        self._serialPort = QtSerialPort.QSerialPort(serialPortDescriptor_)
        if not self._serialPort.open(self._serialPort.ReadWrite):
            raise DeviceException(self, 'Failed to open {}.'.format(serialPortDescriptor))
        if not self._serialPort.setBaudRate(self._serialPort.Baud19200):
            raise DeviceException(self, 'Failed to set serial port {} to 19200 baud.'.format(serialPortDescriptor))
        if not self._serialPort.setFlowControl(self._serialPort.HardwareControl):
            raise DeviceException(self, 'Failed to set serial port {} to 19200 baud.'.format(serialPortDescriptor))
