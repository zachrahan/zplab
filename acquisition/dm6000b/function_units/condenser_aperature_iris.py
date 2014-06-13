# Copyright 2014 WUSTL ZPLAB
# Erik Hvatum (ice.rikh@gmail.com)

import copy
import enum
from PyQt5 import QtCore
from acquisition.device import DeviceException
from acquisition.dm6000b.enums import Method
from acquisition.dm6000b.function_unit import FunctionUnit
from acquisition.dm6000b.packet import Packet, InvalidPacketReceivedException, TruncatedPacketReceivedException

class CondeserApertureIris(FunctionUnit):
    minOpennessChanged = QtCore.pyqtSignal(int)
    maxOpennessChanged = QtCore.pyqtSignal(int)
    opennessChanged = QtCore.pyqtSignal(int)

    def __init__(self, dm6000b, deviceName='Condensor Aperture Iris'):
        super().__init__(dm6000b, deviceName, 84)
        # Subscribe to openness changed notification events
        self._transmit(Packet(self, cmdCode=3, parameter='0 1'))
        # Get min/max openness values
        self._minOpenness = None
        self._maxOpenness = None
        self.refreshMinMaxOpenness()
        # Get current openness
        self._openness = None
        self._transmit(Packet(self, cmdCode=23)

    def __del__(self):
        # Unsubscribe from openness change notification events
        self._transmit(Packet(self, cmdCode=3, parameter='0 0'))
        FunctionUnit.__del__(self)

    def _processReceivedPacket(self, txPacket, rxPacket):
        if rxPacket.statusCode == 0:

            if rxPacket.cmdCode == 28:
                # Response to min openness query
                minOpenness = int(rxPacket.parameter)
                if minOpenness != self._minOpenness:
                    self._minOpenness = minOpenness
                    self.minOpennessChanged.emit(self._minOpenness)

            elif rxPacket.cmdCode == 27:
                # Response to max openness query
                maxOpenness = int(rxPacket.parameter)
                if maxOpenness != self._maxOpenness:
                    self._maxOpenness = maxOpenness
                    self.maxOpennessChanged.emit(self._maxOpenness)

            elif rxPacket.cmdCode == 23:
                # Openness changed notification event or response to openness query
                openness = int(rxPacket.parameter)
                if openness != self._openness:
                    self._openness = openness
                    self.opennessChanged.emit(self._openness)

        elif rxPacket.cmdCode == 3:
            raise DeviceException(self, 'Failed to register for change notification events.  If you have recently ' +
                                        'upgraded your DM6000B\'s firmware, this probably happened because Leica added ' +
                                        'more events for this function unit, and the number of 0 or 1 values in ' +
                                        'event registration packets (command code 3) must exactly match the number ' +
                                        'of events supported.  Fixing this should just be a matter of adding one more ' +
                                        '" 0" at a time to the parameter string for this function unit\'s cmdCode 3 ' +
                                        'packet constructor calls until it starts working again.')

        elif rxPacket.cmdCode == 22:
            e = 'Failed to set openness to {}.  For the current objective, openness must be in the range [{}, {}].'
            raise DeviceException(self, e.format(txPacket.parameter, self._minOpenness, self._maxOpenness))

    def refreshMinMaxOpenness(self):
        # Get min
        self._transmit(Packet(self, cmdCode=28))
        # Get max
        self._transmit(Packet(self, cmdCode=27))

    @QtCore.pyqtProperty(int, notify=minOpennessChanged)
    def minOpenness(self):
        return self._minOpenness

    @QtCore.pyqtProperty(int, notify=maxOpennessChanged)
    def maxOpenness(self):
        return self._maxOpenness

    @QtCore.pyqtProperty(int, notify=opennessChanged)
    def openness(self):
        return self._openness

    @openness.setter
    def openness(self, openness):
        self._transmit(Packet(self, cmdCode=22, parameter=str(openness)))
