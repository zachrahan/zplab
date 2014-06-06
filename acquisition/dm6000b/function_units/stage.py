# Copyright 2014 WUSTL ZPLAB
# Erik Hvatum (ice.rikh@gmail.com)

from PyQt5 import QtCore
from acquisition.device import DeviceException
from acquisition.dm6000b.function_unit import FunctionUnit
from acquisition.dm6000b.packet import Packet, InvalidPacketReceivedException, TruncatedPacketReceivedException

class Stage(FunctionUnit):
    '''This Device represents an interface to any of three separate DM6000B "function units" (in Leica terminology).
    These are the Z-DRIVE (function code 71), X-AXIS (72), Y-AXIS (73).  This Device is meant to act as a subdevice of
    Dm6000b and, as such, depends on its parent to send requests to the DM6000B and to deliver responses from it.'''

    posChanged = QtCore.pyqtSignal(int)

    def __init__(self, dm6000b, deviceName, funitCode):
        super().__init__(dm6000b, deviceName, funitCode)
        self._pos = None
        self.refreshPos()

    def _processReceivedPacket(self, txPacket, rxPacket):
        if rxPacket.statusCode == 0:
            if rxPacket.cmdCode in (22, 23):
                self._pos = int(rxPacket.parameter)
                self.posChanged.emit(self._pos)
                print('requested pos: {} new pos: {}'.format(int(txPacket.parameter) if txPacket is not None and txPacket.cmdCode == 22 else '(none)', self._pos))
        if rxPacket.statusCode == 3:
            if rxPacket.cmdCode == 22:
                # The user requested that the stage move somewhere, but the stage failed to reach the requested position.
                # The scope's reply for the failed move contains as a parameter the requested position, not the position
                # reached.  So, we must retrieve that value as the pos attribute is expected to contain the new value
                # once the device stops being busy after issuance of a move command (whether successful or not).
                self.refreshPos()

    @QtCore.pyqtProperty(int, notify=posChanged)
    def pos(self):
        return self._pos

    @pos.setter
    def pos(self, pos):
        self._transmit(Packet(self, line=None, cmdCode=22, parameter=str(pos)))

    def refreshPos(self):
        self._transmit(Packet(self, line=None, cmdCode=23))
