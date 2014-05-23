# Copyright 2014 WUSTL ZPLAB
# Erik Hvatum (ice.rikh@gmail.com)

from PyQt5 import QtCore, QtSerialPort
import re
import sys
from acquisition.device import Device, DeviceException

class Dm6000b(Device):
    # Signals used to command _DeviceWorker
    _workerSendLineSignal = QtCore.pyqtSignal(str)

    def __init__(self, parent=None, deviceName='Leica DM6000B', serialPortDescriptor='/dev/ttyScope', timeout=1.0):
        '''timeout unit is seconds.'''
        super().__init__(parent, deviceName)

        # Note: QSerialPortInfo, which handles locating the serial port device from a serial port descriptor string, prepends
        # "/dev/" to the descriptor string.  PySerial does not do this, so we generally use full paths which include the /dev/
        # part and chop off the /dev/ when passing to QSerialPort classes.
        match = re.match(r'/dev/([^/]+)', serialPortDescriptor)
        if match:
            serialPortDescriptor_ = match.group(1)
        else:
            serialPortDescriptor_ = serialPortDescriptor

        serialPort = QtSerialPort.QSerialPort(serialPortDescriptor_)

        if not serialPort.open(serialPort.ReadWrite):
            raise DeviceException(self, 'Failed to open {}.'.format(serialPortDescriptor))

        if not serialPort.setBaudRate(serialPort.Baud115200):
            raise DeviceException(self, 'Failed to set serial port {} to 115200 baud.'.format(serialPortDescriptor))

        if not serialPort.setFlowControl(serialPort.SoftwareControl):
            raise DeviceException(self, 'Failed to set serial port {} to software flow control.'.format(serialPortDescriptor))

        self._worker = _DeviceWorker(self, serialPort)
        self._thread = QtCore.QThread(self)
        self._thread.setObjectName(self.deviceName + ' - DEVICE THREAD')
        self._thread.finished.connect(self._thread.deleteLater, QtCore.Qt.QueuedConnection)
        self.deviceNameChanged.connect(self._worker.deviceNameChangedSlot, QtCore.Qt.QueuedConnection)
        self._workerSendLineSignal.connect(self._worker.sendLineSlot, QtCore.Qt.QueuedConnection)
        self._worker.receivedLineSignal.connect(self._workerReceivedLineSlot, QtCore.Qt.QueuedConnection)
        self._thread.start()
        self._worker.moveToThread(self._thread)

    def __del__(self):
        self._thread.quit()
        self._thread.wait()

    def _workerReceivedLineSlot(self, line):
        print('Got line: "{}".'.format(line))


class _DeviceWorker(QtCore.QObject):
    # Signals used to notify Device
    receivedLineSignal = QtCore.pyqtSignal(str)

    def __init__(self, device, serialPort):
        # NB: A QObject can not be moved to another thread if it has a parent.  Otherwise, _DeviceWorker would be parented to its
        # Device by replacing "None" with "device" in the following line.
        super().__init__(None)
        self.device = device
        self.serialPort = serialPort
        # It is convenient to parent the serialPort to the worker so that the serialPort object is automatically moved to another
        # thread along with _DeviceWorker
        self.serialPort.setParent(self)
        self.serialPort.error.connect(self.serialPortErrorSlot, QtCore.Qt.DirectConnection)
        self.serialPort.readyRead.connect(self.serialPortBytesReadySlot, QtCore.Qt.DirectConnection)
        self.buffer = ''

    def serialPortErrorSlot(self, serialPortError):
        print('Serial port error #{} ({}).'.format(serialPortError, self.serialPort.errorString()), file=sys.stderr)

    def serialPortBytesReadySlot(self):
        inba = self.serialPort.readAll()
        #TODO: actually do something when there's an error rather than silently slacking off
        if self.serialPort.error() == self.serialPort.NoError:
            prevBufLen = len(self.buffer)
            self.buffer += inba.data().decode('utf-8')
            # Note: we search one back from start of new data as crlf my straddle the end of the previous read and the start of the
            # current one
            crLoc = self.buffer.find('\r', max(prevBufLen - 1, 0))
            if crLoc < 0:
                # No end of line yet
                pass
            else:
                line = self.buffer[:crLoc]
                self.buffer = self.buffer[crLoc + 1:]
                self.receivedLineSignal.emit(line)

    def deviceNameChangedSlot(self, deviceName):
        self.setObjectName(deviceName + ' - DEVICE THREAD WORKER')
        self.device._thread.setObjectName(deviceName + ' - DEVICE THREAD')

    def sendLineSlot(self, line):
        self.serialPort.write(line + '\r')
