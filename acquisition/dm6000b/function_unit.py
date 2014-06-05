# Copyright 2014 WUSTL ZPLAB
# Erik Hvatum (ice.rikh@gmail.com)

from enum import Enum
from PyQt5 import QtCore
from acquisition.dm6000b.packet import Packet
from acquisition.device import Device, DeviceException

class FunctionUnit(Device):
    class State(Enum):
        Ready = 0
        Busy = 1
        BusyCancellable = 2
        Cancelling = 3
        Bad = 4

    stateChanged = QtCore.pyqtSignal(State)
    _packetReceivedSignal = QtCore.pyqtSignal(Packet)

    def __init__(self, dm6000b, deviceName, funitCode):
        super().__init__(dm6000b, deviceName)
        self._funitCode = funitCode
        # Using self.parent() in any case where a reference to dm6000 is needed yields the same results, but required
        # 50.5 microseconds during testing, whereas self.dm6000b took only 83.6 nanoseconds
        self.dm6000b = dm6000b
        if self._funitCode in self.dm6000b._funitSubdevices:
            raise DeviceException(self, 'Another subdevice is already registered to receive responses for function unit {}.'.format(self._funitCode))
        self.dm6000b._funitSubdevices[self._funitCode] = self
        self._packetReceivedSignal.connect(self._packetReceivedSlot, QtCore.Qt.QueuedConnection)

    def _packetReceivedSlot(self, packet):
        # Override in descendant
        raise NotImplementedError()
