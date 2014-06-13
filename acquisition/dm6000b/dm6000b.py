# Copyright 2014 WUSTL ZPLAB
# Erik Hvatum (ice.rikh@gmail.com)

import copy
from PyQt5 import QtCore, QtSerialPort
import re
from acquisition.device import Device, DeviceException, ThreadedDevice, ThreadedDeviceWorker
from acquisition.dm6000b.enums import ImmersionOrDry, Method
from acquisition.dm6000b.function_unit import FunctionUnit
from acquisition.dm6000b.function_units.condenser_aperature_iris import CondenserApertureIris
from acquisition.dm6000b.function_units.cube_turret import CubeTurret
from acquisition.dm6000b.function_units.dic_turret import DicTurret
from acquisition.dm6000b.function_units.lamp import Lamp
from acquisition.dm6000b.function_units.main import MainFunctionUnit
from acquisition.dm6000b.function_units.objective_turret import ObjectiveTurret
from acquisition.dm6000b.function_units.stage import Stage
from acquisition.dm6000b.packet import Packet, InvalidPacketReceivedException, TruncatedPacketReceivedException

class Dm6000b(ThreadedDevice):
    # Signals used to command _DeviceWorker
    _workerSendLineSignal = QtCore.pyqtSignal(str)
    _workerSendPacketSignal = QtCore.pyqtSignal(Packet)

    def __init__(self, parent=None, deviceName='Leica DM6000B', serialPortDescriptor='/dev/ttyScope', timeout=1.0):
        '''timeout unit is seconds.'''
        super().__init__(_Dm6000bWorker(self), parent, deviceName)

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

        self._workerSendLineSignal.connect(self._worker.sendLineSlot, QtCore.Qt.QueuedConnection)
        self._workerSendPacketSignal.connect(self._worker.sendPacketSlot, QtCore.Qt.QueuedConnection)
        self._worker.receivedUnhandledLineSignal.connect(self._workerReceivedUnhandledLineSlot, QtCore.Qt.BlockingQueuedConnection)

        self._worker.initPort(serialPort)

        # Maps "function unit" code -> subdevice to which responses from the scope with that function unit code should be routed
        self._funitSubdevices = {}

        self.main = MainFunctionUnit(self)

        self.cubeTurret = CubeTurret(self)
        self.lamp = Lamp(self)
        self.objectiveTurret = ObjectiveTurret(self)
        self.condenserApertureIris = CondenserApertureIris(self)
        # Condenser aperture iris max openness varies with objective, but there is no provision for change event notification
        # upon iris min/max openness modification.  Therefore, we must refresh min/max upon objective change.
        self.objectiveTurret.objectiveChanged.connect(self._objectiveChangedSlot)
        self.dicTurret = DicTurret(self)
        self.stageX = Stage(self, 'Stage X Axis Function Unit', 72)
        self.stageY = Stage(self, 'Stage Y Axis Function Unit', 73)
        self.stageZ = Stage(self, 'Stage Z Axis Function Unit', 71)

    def _objectiveChangedSlot(self, objective):
        # Only refresh iris min/max openness if the turret has reached an occupied position
        if objective is not None:
            self.condenserApertureIris.refreshMinMaxOpenness()

    def _workerReceivedUnhandledLineSlot(self, line):
        print('Received unhandled response from "{}":\n\t"{}".'.format(self.deviceName, line))

    def waitForReady(self, timeout=None):
        '''Block until Device State changes from Busy.  Calling this function from a thread other than that owning
        the Dm6000b is not safe and will create a race condition likely resulting in this function never returning.
        NB: the thread owning the Dm6000b instance and the Dm6000b instance's worker thread are not to be confused.
        Somehow calling waitForReady(..) from the worker thread is also unsafe.'''
        for subdevice in self._funitSubdevices.values():
            subdevice.waitForReady(timeout)

class _Dm6000bWorker(ThreadedDeviceWorker):
    # Signals used to notify Device
    receivedUnhandledLineSignal = QtCore.pyqtSignal(str)

    def __init__(self, device):
        super().__init__(device)

    def initPort(self, serialPort):
        '''The serial port is opened and set up on the main thread so that if an error occurs, an exception can be thrown
        that will unwind back to the Dm6000b(..) constructor call in the users's code.  Because we don't really want to
        instantiate QSerialPort in Dm6000b.__init__(..) before calling Dm6000b's super().__init__(..), the QSerialPort instance
        is not available to pass to _Dm6000bWorker's constructor.  Thus, this function, to be called by Dm6000b after the
        parent class's construction.'''
        self.serialPort = serialPort
        self.serialPort.moveToThread(self.device._thread)
        self.serialPort.setParent(self)
        self.serialPort.error.connect(self.serialPortErrorSlot, QtCore.Qt.DirectConnection)
        self.serialPort.readyRead.connect(self.serialPortBytesReadySlot, QtCore.Qt.DirectConnection)
        self.buffer = ''

    def serialPortErrorSlot(self, serialPortError):
        self.device._warn('Serial port error #{} ({}).'.format(serialPortError, self.serialPort.errorString()))

    def serialPortBytesReadySlot(self):
        inba = self.serialPort.readAll()
        # Note: Serial port errors are handled by serialPortErrorSlot which has already been called during execution of the readAll
        # in the line above if an error occurred.  If an exception was thrown by serialPortErrorSlot, it passes through the readAll
        # and causes this function to exit (notice readAll is not in a try block).  If an exception was not thrown but the serial port
        # remains in a bad state, whatever is in the serial port buffer is assumed to be junk and is ignored (the condition of the if
        # statement below evaluates to false and inba goes out of scope without being parsed).
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
                response = Packet(self.device, line)
                if response.funitCode in self.device._funitSubdevices:
                    self.device._funitSubdevices[response.funitCode]._packetReceivedSignal.emit(response)
                else:
                    self.receivedUnhandledLineSignal.emit(line)

    def sendLineSlot(self, line):
        self.serialPort.write(line + '\r')

    def sendPacketSlot(self, packet):
        self.serialPort.write(str(packet))
