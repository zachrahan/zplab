# Copyright 2014 WUSTL ZPLAB
# Erik Hvatum (ice.rikh@gmail.com)

from PyQt5 import QtCore
from acquisition.acquisition_exception import AcquisitionException

class Device(QtCore.QObject):
    deviceNameChanged = QtCore.pyqtSignal(str)
    blockChanged = QtCore.pyqtSignal()

    def __init__(self, parent=None, deviceName='UNNAMED DEVICE'):
        QtCore.QObject.__init__(self, parent)
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

class ThreadedDevice(Device):
    def __init__(self, worker, parent=None, deviceName='UNNAMED THREADED DEVICE'):
        super().__init__(parent, deviceName)
        self._worker = worker
        self._thread = QtCore.QThread(self)
        self._thread.setObjectName(self.deviceName + ' - DEVICE THREAD')
        self._thread.finished.connect(self._thread.deleteLater, QtCore.Qt.QueuedConnection)
        self.deviceNameChanged.connect(self._worker.deviceNameChangedSlot, QtCore.Qt.QueuedConnection)
        self._thread.start()
        self._worker.moveToThread(self._thread)
        self.destroyed.connect(self._destroyedSlot)

    def _destroyedSlot(self):
        self._thread.quit()
        self._thread.wait()

class ThreadedDeviceWorker(QtCore.QObject):
    def __init__(self, device):
        # NB: A QObject can not be moved to another thread if it has a parent.  Otherwise, _DeviceWorker would be parented to its
        # Device by replacing "None" with "device" in the following line.
        super().__init__(None)
        self.device = device

    def deviceNameChangedSlot(self, deviceName):
        self.setObjectName(deviceName + ' - DEVICE THREAD WORKER')
        self.device._thread.setObjectName(deviceName + ' - DEVICE THREAD')

#class OmniSyncPyQtSig(QtCore.QObject):
#    '''As in, "omni-scynchronous".'''
#    class _ArgsHolder:
#        def __init__(self, *args, **kwargs):
#            self._args = args
#            self._kwargs = kwargs
#
#    class _RetHolder:
#        def __init__(self, exception):
#            self._exception = exception
#            self._ret = None
#
#    class _BothHolder:
#        def __init__(self, argsHolder):
#            self._argsHolder = argsHolder
#            self._retHolder = None
#
#    _asyncSignal = QtCore.pyqtSignal(_ArgsHolder)
#    _asyncCompletionSignal = QtCore.pyqtSignal(_RetHolder)
#    _syncSignal = QtCore.pyqtSignal(_BothHolder)
#
#    def __init__(self, device, handler):
#        self._device = device
#        self._handler = handler
#
#    def __call__(self, *args, **kwargs):
#        bothHolder = self._BothHolder(self._ArgsHolder(*args, **kwargs))
#        if self._device.block:
#            self._syncSignal.emit(bothHolder)
#            if bothHandler._retHolder._exception is not None:
#                raise bothHandler._retHolder._exception
#            return bothHandler._retHolder._ret
#        else:
#            self._asyncSignal.emit()
