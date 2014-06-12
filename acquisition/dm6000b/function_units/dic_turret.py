# Copyright 2014 WUSTL ZPLAB
# Erik Hvatum (ice.rikh@gmail.com)

import copy
import enum
from PyQt5 import QtCore
from acquisition.device import DeviceException
from acquisition.dm6000b.enums import Method
from acquisition.dm6000b.function_unit import FunctionUnit
from acquisition.dm6000b.packet import Packet, InvalidPacketReceivedException, TruncatedPacketReceivedException

class DicTurret(FunctionUnit):
    _InitPhase = enum.Enum('_InitPhase', 'MinPos MaxPos MinFinePos MaxFinePos EnumerateNames Done')

    prismChanged = QtCore.pyqtSignal(str)
    finePosChanged = QtCore.pyqtSignal(int)

    def __init__(self, dm6000b, deviceName='DIC Turret'):
        super().__init__(dm6000b, deviceName, 85)
        # So that we don't get confused while initing, unsubscribe from prism change and fine pos change
        # notification events.  Note that this registration takes TWO boolean arguments, whereas the manual
        # indicates that it should take just ONE ("The serial interface documentation for the stands
        # DM4000, DM5000, DM6000; Version 1.5; August 2010", DM456K_SER_REF.pdf).
        self._transmit(Packet(self, cmdCode=3, parameter='0 0'))
        self._currentPrismName = None
        self._currentPrismFinePos = None
        # prism names -> Prism positions
        self._prismNamePositions = {}
        # prism positions -> prism names
        self._positionPrismNames = {}
        # Begin scanning by requesting min prism position (scanning will continue once this value is retrieved)
        self._initPhase = self._InitPhase.MinPos
        self._transmit(Packet(self, cmdCode=29))

    def __del__(self):
        # Unsubscribe from cube change and fine pos change notification events
        self._transmit(Packet(self, cmdCode=3, parameter='0 0'))
        FunctionUnit.__del__(self)

    def _postEnumerationInit(self):
        # Get curret cube
        self._transmit(Packet(self, cmdCode=23))
        # Get current fine pos
        self._transmit(Packet(self, cmdCode=41))
        # Subscribe to cube change and fine pos change notification events
        self._transmit(Packet(self, cmdCode=3, parameter='1 1'))

    def _processReceivedPacket(self, txPacket, rxPacket):
        if self._initPhase == self._InitPhase.Done:
            self._processReceivedNormalPacket(txPacket, rxPacket)
        else:
            self._processReceivedInitPacket(txPacket, rxPacket)

    def _processReceivedNormalPacket(self, txPacket, rxPacket):
        if rxPacket.statusCode == 0:

            if rxPacket.cmdCode == 23:
                # Prism change notification event or response to current prism query
                pos = int(rxPacket.parameter)
                if pos in self._positionPrismNames:
                    # Turret moved to occupied position
                    prismName = self._positionPrismNames[pos]
                else:
                    # Turret moved to empty position
                    prismName = None

                if prismName != self._currentPrismName:
                    self._currentPrismName = prismName
                    self.prismChanged.emit(self._currentPrismName)

            elif rxPacket.cmdCode == 41:
                # Current prism's fine position value change notification event or response to current prism
                # fine position query
                if self._currentPrismName is None:
                    # cmdCode 41 notification is always received after 23 notification.  So, self._currentPrismName
                    # is up to date at this point, and it indicates that the DIC turret is currently at an
                    # unoccupied position (ie, no prism).  It is not possible to set the fine position value
                    # for an empty prism; any attempt to do so fails to change the fine position value away from
                    # zero.  The fine position value for an empty prism is not a meaningful value and is better
                    # thought of as being undefined, which is how we present it, although the DM6000B insists that
                    # this meaningless value is always zero.  This odd behavior is probably an artifact of Leica's
                    # DM6000B firmware implementation particulars - perhaps it would have been supremely inconvenient
                    # to return dash or an empty string rather than zero.
                    finePos = None
                else:
                    finePos = int(rxPacket.parameter)

                if finePos != self._currentPrismFinePos:
                    self._currentPrismFinePos = finePos
                    self.finePosChanged.emit(self._currentPrismFinePos)

    def _processReceivedInitPacket(self, txPacket, rxPacket):
        if rxPacket.statusCode == 0:

            if rxPacket.cmdCode == 29:
                # Response to turret minimum position query
                if self._initPhase != self._InitPhase.MinPos:
                    raise DeviceException(self, 'Received data out of order during init.')
                self._minPos = int(rxPacket.parameter)
                self._initPhase = self._InitPhase.MaxPos
                self._transmit(Packet(self, cmdCode=30))

            elif rxPacket.cmdCode == 30:
                # Response to turret maximum position query
                if self._initPhase != self._InitPhase.MaxPos:
                    raise DeviceException(self, 'Received data out of order during init.')
                self._maxPos = int(rxPacket.parameter)
                self._initPhase = self._InitPhase.MinFinePos
                self._transmit(Packet(self, cmdCode=45))

            elif rxPacket.cmdCode == 45:
                # Reponse to minimum fine position query
                if self._initPhase != self._InitPhase.MinFinePos:
                    raise DeviceException(self, 'Received data out of order during init.')
                self._minFinePos = int(rxPacket.parameter)
                self._initPhase = self._InitPhase.MaxFinePos
                self._transmit(Packet(self, cmdCode=46))

            elif rxPacket.cmdCode == 46:
                # Response to maximum fine position query
                if self._initPhase != self._InitPhase.MaxFinePos:
                    raise DeviceException(self, 'Received data out of order during init.')
                self._maxFinePos = int(rxPacket.parameter)
                self._initPhase = self._InitPhase.EnumerateNames
                self._positionAwaitingInitResponse = self._minPos
                self._transmit(Packet(self, cmdCode=27, parameter=str(self._positionAwaitingInitResponse)))

            elif rxPacket.cmdCode == 27:
                # Response to prism name query
                if self._initPhase != self._InitPhase.EnumerateNames:
                    raise DeviceException(self, 'Received data out of order during init.')
                name = rxPacket.parameter.strip(' ')
                if name == '-':
                    # Empty position
                    pass
                elif len(name) == 0:
                    e = 'Received zero-length or whitespace only name query response for prism at position {}.'
                    raise InvalidPacketReceivedException(self, e.format(self._positionAwaitingInitResponse))
                elif name in self._prismNamePositions:
                    e = 'More than one DIC prism is named "{}".  Because this application identifies DIC prisms by '
                    e+= 'name, duplicate DIC prism names are not supported.'
                    raise DeviceException(self, e.format(name))
                self._prismNamePositions[name] = self._positionAwaitingInitResponse
                self._positionPrismNames[self._positionAwaitingInitResponse] = name
                if self._positionAwaitingInitResponse < self._maxPos:
                    self._positionAwaitingInitResponse += 1
                    self._transmit(Packet(self, cmdCode=27, parameter=str(self._positionAwaitingInitResponse)))
                else:
                    self._initPhase = self._InitPhase.Done
                    if len(self._prismNamePositions) == 0:
                        # All DIC turret positions are empty, so we're done initing.  It is unlikely - although possible
                        # - that the DIC turret is truly empty, so the user is warned of this state of affairs.
                        self._warn('All DIC turret positions appear to be unoccupied!')
                    else:
                        self._postEnumerationInit()

        elif rxPacket.cmdCode == 3:
            raise DeviceException(self, 'Failed to register for change notification events.  If you have recently ' +
                                        'upgraded your DM6000B\'s firmware, this probably happened because Leica added ' +
                                        'more events for this function unit, and the number of 0 or 1 values in ' +
                                        'event registration packets (command code 3) must exactly match the number ' +
                                        'of events supported.  Fixing this should just be a matter of adding one more ' +
                                        '" 0" at a time to the parameter string for this function unit\'s cmdCode 3 ' +
                                        'packet constructor calls until it starts working again.')

    @QtCore.pyqtProperty(str, notify=prismChanged)
    def prism(self):
        '''Note that there is no associated prism setter.  This is very much intentional - prisms are switched as
        a result of switching objectives or methods.  The command to explicitly change to a different prism (85022)
        modifies the current objective's configuration, permanantly associating the new prism with the current method
        of the current objective.  This is not something that can be done through the physical scope interface
        screen and is probably not a behavior that anyone aside from a Leica engineer would ever anticipate.'''
        return self._currentPrismName

    @QtCore.pyqtProperty(int, notify=finePosChanged)
    def finePos(self):
        '''Note that modifying the current prism fine position does not permanantly alter the fine position value
        associated with the current method of the current objective.'''
        return self._currentPrismFinePos

    @finePos.setter
    def finePos(self, finePos):
        if self._currentPrismName is None:
            raise DeviceException(self, 'Can not set current DIC prism fine position; the DIC turret is currently ' +
                                        'at an empty position (ie, no prism is in the beam path).')
        if finePos < self._minFinePos or finePos > self._maxFinePos:
            e = 'finePos value must lie in the range [{}, {}].  The specified value, {}, does not.'
            raise DeviceException(self, e.format(self._minFinePos, self._maxFinePos, finePos))
        if finePos != self._currentPrismFinePos:
            self._transmit(Packet(self, cmdCode=40, parameter=str(finePos)))
