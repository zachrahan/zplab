# Copyright 2014 WUSTL ZPLAB
# Erik Hvatum (ice.rikh@gmail.com)

from enum import Enum
from PyQt5 import QtCore
import threading
from acquisition.dm6000b.packet import Packet
from acquisition.device import Device, DeviceException, DeviceTimeoutException

class FunctionUnit(Device):
    class State(Enum):
        Ready = 0
        Busy = 1
        Bad = 2

    stateChanged = QtCore.pyqtSignal()
    _packetReceivedSignal = QtCore.pyqtSignal(Packet)

    def __init__(self, dm6000b, deviceName, funitCode):
        super().__init__(dm6000b, deviceName)
        self._state = self.State.Ready
        self._outstanding = {}
        self._funitCode = funitCode
        # Using self.parent() in any case where a reference to dm6000 is needed yields the same results, but required
        # 50.5 microseconds during testing, whereas self.dm6000b took only 83.6 nanoseconds
        self.dm6000b = dm6000b
        if self._funitCode in self.dm6000b._funitSubdevices:
            raise DeviceException(self, 'Another subdevice is already registered to receive responses for function unit {}.'.format(self._funitCode))
        self.dm6000b._funitSubdevices[self._funitCode] = self
        self._packetReceivedSignal.connect(self._packetReceivedSlot, QtCore.Qt.QueuedConnection)

    def _packetReceivedSlot(self, packet):
        txPacket = None
        # NB: an event notification is sent unprompted and therefore has no associated request
        if not packet.isEventNotification and packet.cmdCode in self._outstanding:
            txPackets = self._outstanding[packet.cmdCode]
            # Presumably the DM6000B reponds to requests for the same function unit and command in FIFO order, so if no
            # request is found matching the response, the oldest request is assumed to have provoked the response
            if packet.statusCode != 0:
                txPacket = txPackets[0]
                del txPackets[0]
            else:
                for i, tp in enumerate(txPackets):
                    if tp.parameter == packet.parameter:
                        txPacket = tp
                        del txPackets[i]
                        break
                if txPacket is None:
                    txPacket = txPackets[0]
                    del txPackets[0]
            if len(txPackets) == 0:
                del self._outstanding[packet.cmdCode]
#       if self._funitCode == 85:
#           print('got response for "{}":  funitCode: {}, statusCode: {}, cmdCode: {}, parameter: {}, outstanding: {}'.format(self.deviceName, packet.funitCode, packet.statusCode, packet.cmdCode, packet.parameter, len(self._outstanding)))
        self._processReceivedPacket(txPacket, packet)
        self._updateState()

    def _processReceivedPacket(self, txPacket, rxPacket):
        raise NotImplementedError('Pure virtual function called.')

    def _updateState(self):
        if len(self._outstanding) == 0:
            if self._state == self.State.Busy:
                self._state = self.State.Ready
                self.stateChanged.emit()
        else:
            if self._state == self.State.Ready:
                self._state = self.State.Busy
                self.stateChanged.emit()

    def _transmit(self, packet):
        if packet.cmdCode not in self._outstanding:
            self._outstanding[packet.cmdCode] = [packet]
        else:
            self._outstanding[packet.cmdCode].append(packet)
#       if self._funitCode == 85:
#           print('sent to "{}":  funitCode: {}, cmdCode: {}, parameter: {}, outstanding: {}'.format(self.deviceName, packet.funitCode, packet.cmdCode, packet.parameter, len(self._outstanding)))
        self.dm6000b._workerSendPacketSignal.emit(packet)
        self._updateState()

    @QtCore.pyqtProperty(State, notify=stateChanged)
    def state(self):
        return self._state

    def waitForReady(self, timeout=None):
        '''Block until Device State changes from Busy.  If timeout seconds elapse while Device State remains Busy, a
        DeviceTimeoutException is thrown.  If Device State was Bad when waitForReady(..) was called, or if Device State
        changes from Busy to Bad during the wait, a DeviceException is thrown.  Note that this function relies on being called
        from the thread owning the Device (normally the main thread or GUI thread).  Calling it from another thread creates
        a race condition: the main thread's event loop may be running and, if it is, it will eat a stateChanged signal
        emitted before we can start executing our local event loop.'''
        if self._state == self.State.Busy:
            self._waitForSignal(self.stateChanged, timeout)
        if self._state == self.State.Bad:
            raise DeviceException(self, 'Device is in bad state.')
