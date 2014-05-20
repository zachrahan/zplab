# Copyright 2014 WUSTL ZPLAB
# Drew Sinha <sinhad@wusm.wustl.edu> 
# Erik Hvatum (ice.rikh@gmail.com)

import serial
from acquisition.device import Device, DeviceException

class Peltier(Device):
    def __init__(self, serialPortDescriptor='/dev/ttyPeltier', name='Incubator Peltier Controller'):
        super().__init__(name)
        self._appendTypeName('Peltier')

        self._serialPort = serial.Serial(serialPortDescriptor, 9600, timeout=1)
        if not self._serialPort.isOpen():
            raise DeviceException(self, 'Failed to open {}.'.format(serialPortDescriptor))
