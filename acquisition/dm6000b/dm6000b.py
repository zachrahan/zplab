# Copyright 2014 WUSTL ZPLAB
# Erik Hvatum (ice.rikh@gmail.com)

from PyQt5 import QtCore, QtSerialPort
import re
import sys
from acquisition.device import Device, DeviceException, ThreadedDevice, ThreadedDeviceWorker
from acquisition.dm6000b.function_unit import FunctionUnit
from acquisition.dm6000b.function_units.stage import Stage
from acquisition.dm6000b.method import Method
from acquisition.dm6000b.packet import Packet, InvalidPacketReceivedException, TruncatedPacketReceivedException

class Dm6000b(ThreadedDevice):
    # Signals used to command _DeviceWorker
    _workerSendLineSignal = QtCore.pyqtSignal(str)
    _workerSendPacketSignal = QtCore.pyqtSignal(Packet)

    # Signals available to user to indicate property value changes
    tlShutterOpenedChanged = QtCore.pyqtSignal(bool)
    ilShutterOpenedChanged = QtCore.pyqtSignal(bool)

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

        self._main = _MainFunctionUnit(self)
        self._lamp = _Lamp(self)
        self.stageX = Stage(self, 'Stage X Axis', 72)
        self.stageY = Stage(self, 'Stage Y Axis', 73)
        self.stageZ = Stage(self, 'Stage Z Axis', 71)

    def __del__(self):
        self._thread.quit()
        self._thread.wait()

    def _workerReceivedUnhandledLineSlot(self, line):
        print('Received unhandled response from "{}":\n\t"{}".'.format(self.deviceName, line))

    def waitForReady(self, timeout=None):
        '''Block until Device State changes from Busy.  Calling this function from a thread other than that owning
        the Dm6000b is not safe and will create a race condition likely resulting in this function never returning.
        NB: the thread owning the Dm6000b instance and the Dm6000b instance's worker thread are not to be confused.
        Somehow calling waitForReady(..) from the worker thread is also unsafe.'''
        for subdevice in self._funitSubdevices.values():
            subdevice.waitForReady(timeout)

    @QtCore.pyqtProperty(list)
    def methods(self):
        '''Index by Method enum value.  For example, to see if "IL DIC" is supported, do dm6000b.methods[Method.IL_DIC]
        (a bool is returned, True if the specified method is supported).'''
        return self._methods.copy()

    @QtCore.pyqtProperty(dict)
    def methodsAsDict(self):
        '''The same as the methods property, except a dict of "Method enum value -> is supported bool" is returned.'''
        return {method : self._methods[method] for method in Method}

    @QtCore.pyqtProperty(bool, notify=tlShutterOpenedChanged)
    def tlShutterOpened(self):
        return self._tlShutterOpened

    @tlShutterOpened.setter
    def tlShutterOpened(self, tlShutterOpened):
        self._lamp._setShutterOpened(0, tlShutterOpened)

    @QtCore.pyqtProperty(bool, notify=ilShutterOpenedChanged)
    def ilShutterOpened(self):
        return self._ilShutterOpened

    @ilShutterOpened.setter
    def ilShutterOpened(self, ilShutterOpened):
        self._lamp._setShutterOpened(1, ilShutterOpened)

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
        print('Serial port error #{} ({}).'.format(serialPortError, self.serialPort.errorString()), file=sys.stderr)

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

class _MainFunctionUnit(FunctionUnit):
    '''Dm6000b can't inherit from both ThreadedDevice and FunctionUnit.  However, a user will expect to find properties for
    the scope "main function unit" as attributes of Dm6000b directly, not as attributes of Dm6000b.mainUnit or somesuch.
    _Dm6000bWorker could route main function unit packets back to its Dm6000b instance, but then
    FunctionUnit._processReceivedPacket and every other aspect of FunctionUnit would need to be reimplemented as a methods
    of Dm6000b, which would be redundant and very confusing.

    Instead, a FunctionUnit _MainFunctionUnit is made that stores all its user accessible properties in its associated
    Dm6000b instance, where they are easily found by the user.'''

    def __init__(self, dm6000b, deviceName='hidden Main Function Unit - properties proxied to Dm6000b'):
        super().__init__(dm6000b, deviceName, 70)
        self.dm6000b._methods = None
        self._transmit(Packet(self, line=None, cmdCode=26))

    def _processReceivedPacket(self, txPacket, rxPacket):
        if rxPacket.statusCode == 0:
            if rxPacket.cmdCode == 26:
                methods = []
                for method in Method:
                    s = rxPacket.parameter[-method.value]
                    if s == '0':
                        methods.append(False)
                    elif s == '1':
                        methods.append(True)
                    else:
                        raise InvalidPacketReceivedException(self, 'Method supported element must be either "0" or "1", not "{}".'.format(s))
                self.dm6000b._methods = methods

class _Lamp(FunctionUnit):
    '''We are not using the DM6000B's lamp; however, TL and IL shutter settings belong to the lamp function unit.  Rather
    than create confusion by adding a user visible lamp subdevice, the lamp function unit's shutter state properties are
    available as properties of the associated Dm6000b instance.
    '''
    def __init__(self, dm6000b, deviceName='hidden Lamp Function Unit - properties proxied to Dm6000b'):
        super().__init__(dm6000b, deviceName, 77)
        self.dm6000b._tlShutterOpened = None
        self.dm6000b._ilShutterOpened = None
        # Subscribe to shutter open/close events
        self._transmit(Packet(self, line=None, cmdCode=3, parameter='0 0 0 0 1 1'))
        # Get current shutter open/close states
        self._transmit(Packet(self, line=None, cmdCode=33))

    def _processReceivedPacket(self, txPacket, rxPacket):
        if rxPacket.statusCode == 0:
            if rxPacket.cmdCode == 33:
                tl, il = rxPacket.parameter.split(' ')
                def toBool(s, n):
                    if s == '0':
                        return False
                    elif s == '1':
                        return True
                    elif s == '-1':
                        print('Your "{}" reports that the {} shutter has encountered a problem.  In fact, '.format(self.dm6000b.deviceName, n) +
                              'the microscope doesn\'t know whether that shutter is even open.  This is generally not an ' +
                              'error you want to be having.  So, I\'m going to go ahead and exit, while you dutifully ' +
                              'attend to your broken microscope, dear user.', sys.stderr)
                        sys.exit(-1)
                    else:
                        raise InvalidPacketReceivedException(self, 'Shutter state value must be either "0", "1", or "-1", but not "{}".'.format(s))
                v = toBool(tl, 'TL')
                if self.dm6000b._tlShutterOpened != v:
                    self.dm6000b._tlShutterOpened = v
                    self.dm6000b.tlShutterOpenedChanged.emit(v)
                v = toBool(il, 'IL')
                if self.dm6000b._ilShutterOpened != v:
                    self.dm6000b._ilShutterOpened = v
                    self.dm6000b.ilShutterOpenedChanged.emit(v)

    def _setShutterOpened(self, idx, opened):
        self._transmit(Packet(self, line=None, cmdCode=32, parameter='{} {}'.format(idx, '1' if opened else '0')))
