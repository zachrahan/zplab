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

    def _processReceivedPacket(self, txPacket, rxPacket):
        print('got response for "{}":  funitCode: {}, statusCode: {}, cmdCode: {}, parameter: {}'.format(self.deviceName, rxPacket.funitCode, rxPacket.statusCode, rxPacket.cmdCode, rxPacket.parameter))
        if rxPacket.statusCode == 0:
            if rxPacket.cmdCode in (22, 23):
                self._pos = int(rxPacket.parameter)
                self.posChanged.emit(self._pos)
                print('requested pos: {} new pos: {}'.format(int(txPacket.parameter) if txPacket.cmdCode == 22 else '(none)', self._pos))

    @QtCore.pyqtProperty(int, notify=posChanged)
    def pos(self):
        return self._pos

    @pos.setter
    def pos(self, pos):
        self._transmit(Packet(self, line=None, funitCode=self._funitCode, cmdCode=22, parameter=str(pos)))
