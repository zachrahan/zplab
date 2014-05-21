# Copyright 2014 WUSTL ZPLAB
# Erik Hvatum (ice.rikh@gmail.com)

import serial
from acquisition.device import Device, DeviceException

class Dm6000b(Device):
    def __init__(self, serialPortDescriptor='/dev/ttyScope', name='Leica DM6000B'):
        super().__init__(name)
        self._appendTypeName('Dm6000b')

        self._serialPort = serial.Serial(serialPortDescriptor, 19200, timeout=1)
        if not self._serialPort.isOpen():
            raise DeviceException(self, 'Failed to open {}.'.format(serialPortDescriptor))
