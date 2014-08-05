# Copyright 2014 WUSTL ZPLAB
# Erik Hvatum (ice.rikh@gmail.com)

from PyQt5 import QtCore
import sys
from acquisition.acquisition_exception import AcquisitionException

class Device(QtCore.QObject):
    deviceNameChanged = QtCore.pyqtSignal(str)

    def __init__(self, parent=None, deviceName='UNNAMED DEVICE'):
        QtCore.QObject.__init__(self, parent)
        self.setObjectName(deviceName)
        self.objectNameChanged.connect(self.deviceNameChanged)

    def __del__(self):
        '''Provided so that all child classes may call Device.__del__(self) for potential forward compatibility in the
        case where this class someday does come to do something important in its destructor.'''
        pass

    def _warn(self, warning):
        print('{}: Warning: {}'.format(self.deviceName, warning), sys.stderr)

    @property
    def deviceName(self):
        '''All QObjects have an objectName Qt property that is exposed via .objectName() and .setObjectName(..).  "objectName"
        is a more general term than would be optimal in this context; "deviceName" would be better.  However, objectName
        exists and is already known to Qt debugging tools, and it would be more confusing to add a deviceName property in
        addition to objectName, so we use objectName for this purpose and provide a deviceName getter, setter, and change
        notification that wrap those of objectName.'''
        return self.objectName()

    @deviceName.setter
    def deviceName(self, deviceName):
        self.setObjectName(deviceName)

    def waitForReady(self):
        '''Overridden by Device implementations in order to offer an efficient method of blocking until all outstanding
        asynchronous operations for that Device complete.  Note that, in general, this method should only be called from the
        thread owning the Device (normally the main thread or GUI thread).'''
        return

    def _waitForSignal(self, signal, timeout=None):
        '''Helper for waitForReady() implementation helper.  If timeout seconds elapse without receiving the signal, a
        DeviceTimeoutException is thrown.  Note that this function relies on being called from the thread owning the Device
        (normally the main thread or GUI thread).  Calling it from another thread creates a race condition: the main thread's
        event loop may be running and, if it is, it will eat the signal we are waiting for if it is emitted before we can
        start executing our local event loop.'''
        timedOut = False
        eventLoop = QtCore.QEventLoop()
        signal.connect(eventLoop.quit)
        if timeout is not None:
            timer = QtCore.QTimer()
            timer.setSingleShot(True)
            def ontimeout():
                nonlocal timedOut
                timedOut = True
                eventLoop.quit()
            timer.timeout.connect(ontimeout)
            timer.start(timeout * 1000)
        eventLoop.exec_()
        if timedOut:
            raise DeviceTimeoutException(self, 'waitForReady(..) timed out.')

class DeviceException(AcquisitionException):
    def __init__(self, device, description):
        super().__init__(description)
        self.device = device

    def __str__(self):
        return repr('{}: {}'.format(self.device.deviceName, self.description))

class DeviceTimeoutException(DeviceException):
    pass

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

    def __del__(self):
        self._thread.quit()
        self._thread.wait()
        Device.__del__(self)

class ThreadedDeviceWorker(QtCore.QObject):
    def __init__(self, device):
        # NB: A QObject can not be moved to another thread if it has a parent.  Otherwise, _DeviceWorker would be parented to its
        # Device by replacing "None" with "device" in the following line.
        super().__init__(None)
        self.device = device

    def deviceNameChangedSlot(self, deviceName):
        self.setObjectName(deviceName + ' - DEVICE THREAD WORKER')
        self.device._thread.setObjectName(deviceName + ' - DEVICE THREAD')
