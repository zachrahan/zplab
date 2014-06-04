# Copyright 2014 WUSTL ZPLAB
# Erik Hvatum (ice.rikh@gmail.com)

from PyQt5 import QtCore
from acquisition.dm6000b.response import Response
from acquisition.device import Device, DeviceException

class Subdevice(Device):
    _responseReceivedSignal = QtCore.pyqtSignal(Response)

    def __init__(self, dm6000b, deviceName, ids):
        super().__init__(dm6000b, deviceName)
        # Using self.parent() in any case where a reference to dm6000 is needed yields the same results, but required
        # 50.5 microseconds during testing, whereas self.dm6000b took only 83.6 nanoseconds
        self.dm6000b = dm6000b

        for id in ids:
            if id in self.dm6000b._idsToSubdevices:
                raise DeviceException(self, 'Another subdevice is already registered to receive responses for function ID {}.'.format(id))
            self.dm6000b._idsToSubdevices[id] = self

        self._responseReceivedSignal.connect(self._responseReceivedSlot, QtCore.Qt.QueuedConnection)

    def _responseReceivedSlot(self, response):
        # Override in descendant
        raise NotImplementedError()
