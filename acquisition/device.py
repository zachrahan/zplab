# Copyright 2014 WUSTL ZPLAB
# Erik Hvatum (ice.rikh@gmail.com)

from PyQt5 import QtCore
from acquisition.acquisition_exception import AcquisitionException

class Device(QtCore.QObject):
    deviceNameChanged = QtCore.pyqtSignal(str)
    blockChanged = QtCore.pyqtSignal()

    def __init__(self, parent=None, deviceName='UNNAMED DEVICE'):
        super().__init__(parent)
        self.setObjectName(deviceName)
        self._block = True
        self.objectNameChanged.connect(self.deviceNameChanged)

    @property
    def deviceName(self):
        '''All QObjects have an objectName Qt property that is exposed via .objectName() and .setObjectName(..).  "objectName" is a more general
        term than would be optimal in this context; "deviceName" would be better.  However, objectName exists and is already known to Qt debugging tools,
        and it would be more confusing to add a deviceName property in addition to objectName, so we use objectName for this purpose and provide a
        deviceName getter, setter, and change notification that wrap those of objectName.'''
        return self.objectName()

    @deviceName.setter
    def deviceName(self, deviceName):
        self.setObjectName(deviceName)

    @QtCore.pyqtProperty(bool, notify=blockChanged)
    def block(self):
        '''If true, forces operations that may be performed either asynchronously or synchronously to execute synchronously, in blocking fashion,
        in the calling thread.'''
        return self._block

    @block.setter
    def block(self, block):
        self._block = block

class DeviceException(AcquisitionException):
    def __init__(self, device, description):
        super().__init__(description)
        self.device = device

    def __str__(self):
        return repr('{}: {}'.format(self.device.deviceName, self.description))
