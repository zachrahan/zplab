# Copyright 2014 WUSTL ZPLAB
# Erik Hvatum (ice.rikh@gmail.com)

import enum
from PyQt5 import QtCore
import re
from acquisition.device import DeviceException
from acquisition.dm6000b.enums import ImmersionOrDry
from acquisition.dm6000b.function_unit import FunctionUnit
from acquisition.dm6000b.packet import Packet, InvalidPacketReceivedException, TruncatedPacketReceivedException

class ObjectiveTurret(FunctionUnit):
    '''AKA "nose piece" AKA "revolver" - that rotating bit of hardware to which objectives of various maginifications
    are attached.  This Device is meant to act as a subdevice of Dm6000b and, as such, depends on its parent to send
    requests to the DM6000B and to deliver responses from it.'''

    _ObjectivesInitPhase = enum.Enum('_ObjectivesInitPhase', 'GetMin GetMax Done')

    immersionOrDryChanged = QtCore.pyqtSignal(ImmersionOrDry)
    objectiveTurretMovingChanged = QtCore.pyqtSignal(bool)
    objectiveChanged = QtCore.pyqtSignal(int)

    def __init__(self, dm6000b, deviceName='Objective Turret Function Unit'):
        super().__init__(dm6000b, deviceName, 76)
        # So that we don't get confused while initing, unsubscribe from all of the objective turret function unit change events
        self._transmit(Packet(self, cmdCode=3, parameter='0 0 0 0 0 0 0 0 0 0'))
        # Begin scanning objectives by requesting min objective index (scanning will continue once this value is retrieved)
        self._objective = None
        self._objectives = {}
        self._positionMagnifications = {}
        self._immersionOrDry = None
        self._moving = None
        self._objectivesInitPhase = self._ObjectivesInitPhase.GetMin
        self._transmit(Packet(self, cmdCode=38))

    def __del__(self):
        # Unsubscribe from all events
        self._transmit(Packet(self, cmdCode=3, parameter='0 0 0 0 0 0 0 0 0 0'))
        FunctionUnit.__del__(self)

    def _postEnumerationInit(self):
        # Get current turrent position
        self._transmit(Packet(self, cmdCode=23))
        # Subscribe to change events for: turret in motion
        self._transmit(Packet(self, cmdCode=3, parameter='1 0 0 0 0 0 0 0 0 0'))

    def _processReceivedPacket(self, txPacket, rxPacket):
        if self._objectivesInitPhase == self._ObjectivesInitPhase.Done:
            self._processReceivedNormalPacket(txPacket, rxPacket)
        else:
            self._processReceivedInitPacket(txPacket, rxPacket)

    def _processReceivedNormalPacket(self, txPacket, rxPacket):
        if rxPacket.statusCode == 0:

            if rxPacket.cmdCode == 4:
                # Response to "is objective turret in motion" query.  (As in, whether the scope is switching between objective
                # turret positions, not whether the turret is moving because the scope itself is moving due to earthquake or
                # perhaps a viking hoisting the scope into a long boat.  We'd have to mount some accelerometers to the scope
                # stand if we wanted that information.)
                vs = rxPacket.parameter.split(' ')
                if vs[2] == '1' and vs[3] == '0':
                    moving = False
                    self._transmit(Packet(self, cmdCode=23))
                elif vs[2] == '0' and vs[3] == '1':
                    moving = True
                else:
                    raise InvalidPacketReceivedException(self, 'Final two parameter values must be "0 1" or "1 0", not "{} {}".'.format(vs[2], vs[3]))

            elif rxPacket.cmdCode == 23:
                self._position = int(rxPacket.parameter)

        elif rxPacket.statusCode == 3:
            if rxPacket.cmdCode == 22:
                # Scope rejected turret position change command
                raise DeviceException(self, 'Failed to switch to {}x objective.  '.format(self._positionMagnifications[int(txPacket.parameter)]) +
                                            'The cause of this is often that the specified objective is not compatible with the current immersionOrDry setting.  '
                                            'Before switching to an immersion objective, set immersionOrDry = "I", and for standard objectives, "D".')

    def _processReceivedInitPacket(self, txPacket, rxPacket):
        if rxPacket.statusCode == 0:

            if rxPacket.cmdCode == 38:
                # Response to minimum objective position index query
                if self._objectivesInitPhase != self._ObjectivesInitPhase.GetMin:
                    raise DeviceException(self, 'Received data out of order during init.')
                self._objectiveMinPosition = int(rxPacket.parameter)
                self._objectivesInitPhase = self._ObjectivesInitPhase.GetMax
                self._transmit(Packet(self, cmdCode=39))

            elif rxPacket.cmdCode == 39:
                # Response to maximum objective position index query
                if self._objectivesInitPhase != self._ObjectivesInitPhase.GetMax:
                    raise DeviceException(self, 'Received data out of order during init.')
                self._objectiveMaxPosition = int(rxPacket.parameter)
                self._objectivesInitPhase = self._ObjectivesInitPhase.Done
                self._postEnumerationInit()

    @QtCore.pyqtProperty(int)
    def position(self):
        return self._position

    @position.setter
    def position(self, position):
        self._transmit(Packet(self, cmdCode=22, parameter=str(position)))
