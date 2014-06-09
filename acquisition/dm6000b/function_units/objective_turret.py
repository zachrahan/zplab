# Copyright 2014 WUSTL ZPLAB
# Erik Hvatum (ice.rikh@gmail.com)

import enum
from PyQt5 import QtCore
import re
from acquisition.device import DeviceException
from acquisition.dm6000b.enums import ImmersionOrDry
from acquisition.dm6000b.function_unit import FunctionUnit
from acquisition.dm6000b.packet import Packet, InvalidPacketReceivedException, TruncatedPacketReceivedException

class Objective:
    def __init__(self, position=None, magnification=None, type_=None):
        self.position = position
        self.magnification = magnification
        self.type_ = type_
    def __repr__(self):
        return 'Objective(position={}, magnification={}, type_={})'.format(self.position, self.magnification, self.type_)

class _ObjectiveTurret(FunctionUnit):
    '''AKA "nose piece" AKA "revolver" - that rotating bit of hardware to which objectives of various maginifications
    are attached.  This Device is meant to act as a subdevice of Dm6000b and, as such, depends on its parent to send
    requests to the DM6000B and to deliver responses from it.'''

    _ObjectivesInitPhase = enum.Enum('_ObjectivesInitPhase', 'GetMin GetMax Enumerate Done')

    def __init__(self, dm6000b, deviceName='hidden Objective Turret Function Unit - properties proxied to Dm6000b'):
        super().__init__(dm6000b, deviceName, 76)
        # So that we don't get confused while initing, unsubscribe from all of the objective turret function unit change events
        self._transmit(Packet(self, cmdCode=3, parameter='0 0 0 0 0 0 0 0 0 0'))
        # Begin scanning objectives by requesting min objective index (scanning will continue once this value is retrieved)
        self._objective = None
        self._objectives = {}
        self._positionMagnifications = {}
        self._objectivesInitPhase = self._ObjectivesInitPhase.GetMin
        self._transmit(Packet(self, cmdCode=38))

    def _postEnumerationInit(self):
        # Get current objective magnification
        self._transmit(Packet(self, cmdCode=33, parameter='a 1'))
        # Get current immsersion or dry state
        self._immersionOrDry = None
        self._transmit(Packet(self, cmdCode=28))
        # Get current objective movement state
        self._moving = None
        self._transmit(Packet(self, cmdCode=4))
        # Subscribe to change events for: turret in motion, objective magnification changed, immersion or dry state change
        self._transmit(Packet(self, cmdCode=3, parameter='1 1 0 0 0 0 1 0 0 0'))

    def _processReceivedPacket(self, txPacket, rxPacket):
        if self._objectivesInitPhase == self._ObjectivesInitPhase.Done:
            self._processReceivedNormalPacket(txPacket, rxPacket)
        else:
            self._processReceivedInitPacket(txPacket, rxPacket)

    def _processReceivedNormalPacket(self, txPacket, rxPacket):
        if rxPacket.statusCode == 0:

            if rxPacket.cmdCode == 4:
                vs = rxPacket.parameter.split(' ')
                if vs[2] == '1' and vs[3] == '0':
                    moving = False
                elif vs[2] == '0' and vs[3] == '1':
                    moving = True
                else:
                    raise InvalidPacketReceivedException(self, 'Final two parameter values must be "0 1" or "1 0", not "{} {}".'.format(vs[2], vs[3]))

                if moving != self._moving:
                    self._moving = moving
                    self.dm6000b.objectiveTurretMovingChanged.emit(self._moving)

            elif rxPacket.cmdCode == 28:
                if rxPacket.parameter == 'D':
                    immersionOrDry = ImmersionOrDry.Dry
                elif rxPacket.parameter == 'I':
                    immersionOrDry = ImmersionOrDry.Immersion
                else:
                    raise InvalidPacketReceivedException(self, 'Parameter must be "D" or "I", not "{}".'.format(rxPacket.parameter))

                if immersionOrDry != self._immersionOrDry:
                    self._immersionOrDry = immersionOrDry
                    self.dm6000b.immersionOrDryChanged.emit(self._immersionOrDry)

            elif rxPacket.cmdCode == 33:
                vs = rxPacket.parameter.split(' ')
                position = int(vs[0])
                par = int(vs[1])
                if par == 1:
                    if position not in self._positionMagnifications:
                        # Current objective turret position is empty
                        objective = None
                    else:
                        magnification = self._positionMagnifications[position]
                        if magnification not in self._objectives:
                            raise DeviceException(self, 'Objective with magnification {}x at position {} '.format(magnification, position) +
                                                        'was not enumerated during initialization.')
                        objective = self._objectives[magnification]
                        if objective.magnification != magnification:
                            e = 'Objective magnification ({}x) for objective at position {} does not match the magnification found during initialization ({}x).'
                            raise DeviceException(self, e.format(magnification, position, objective.magnification))
                        objective = magnification

                    if objective is not self._objective:
                        self._objective = objective
                        self.dm6000b.objectiveChanged.emit(self._objective)
                else:
                    raise DeviceException(self, 'Received extraneous (non-requested) objective parameter data.')

    def _processReceivedInitPacket(self, txPacket, rxPacket):
        if rxPacket.statusCode == 0:

            if rxPacket.cmdCode == 38:
                if self._objectivesInitPhase != self._ObjectivesInitPhase.GetMin:
                    raise DeviceException(self, 'Received data out of order.')
                self._objectiveMinPosition = int(rxPacket.parameter)
                self._objectivesInitPhase = self._ObjectivesInitPhase.GetMax
                self._transmit(Packet(self, cmdCode=39))

            elif rxPacket.cmdCode == 39:
                if self._objectivesInitPhase != self._ObjectivesInitPhase.GetMax:
                    raise DeviceException(self, 'Received data out of order.')
                self._objectiveMaxPosition = int(rxPacket.parameter)
                self._objectivesInitPhase = self._ObjectivesInitPhase.Enumerate
                self._objectivePositionsAwaitingInitResponse = {p:[True, True] for p in range(self._objectiveMinPosition, self._objectiveMaxPosition+1)}
                self._objectivesByPosition = {p:Objective() for p in range(self._objectiveMinPosition, self._objectiveMaxPosition+1)}
                for p in self._objectivePositionsAwaitingInitResponse.keys():
                    self._transmit(Packet(self, cmdCode=33, parameter='{} 1'.format(p)))
                    self._transmit(Packet(self, cmdCode=33, parameter='{} 5'.format(p)))

            elif rxPacket.cmdCode == 33:
                if self._objectivesInitPhase != self._ObjectivesInitPhase.Enumerate:
                    raise DeviceException(self, 'Received data out of order.')
                vs = rxPacket.parameter.split(' ')
                position = int(vs[0])
                par = int(vs[1])
                awaiting = self._objectivePositionsAwaitingInitResponse[position]
                objective = self._objectivesByPosition[position]
                if par == 1:
                    if not awaiting[0]:
                        raise DeviceException(self, 'Received duplicate response for objective magnification.')
                    objective.position = position
                    if vs[2] != '-':
                        objective.magnification = int(vs[2])
                    awaiting[0] = False
                elif par == 5:
                    if not awaiting[1]:
                        raise DeviceException(self, 'Received duplicate response for objective type.')
                    objective.type_ = vs[2]
                    awaiting[1] = False
                else:
                    raise DeviceException(self, 'Received extraneous (non-requested) objective parameter data.')

                if not any(awaiting):
                    del self._objectivePositionsAwaitingInitResponse[position]

                if len(self._objectivePositionsAwaitingInitResponse) == 0:
                    for position, objective in self._objectivesByPosition.items():
                        if objective.magnification is not None:
                            if objective.magnification in self._objectives:
                                raise DeviceException(self, 'More than one objective has {}x magnification.  Because this application identifies objectives ' +
                                                            'by magnification, having multiple objectives of the same magnification on the same objective ' +
                                                            'turret is not supported.')
                            self._objectives[objective.magnification] = objective
                            self._positionMagnifications[objective.position] = objective.magnification
                    self._objectivesInitPhase = self._ObjectivesInitPhase.Done
                    del self._objectivePositionsAwaitingInitResponse
                    del self._objectivesByPosition
                    self._postEnumerationInit()
                        
    def _setObjective(self, magnification):
        if type(magnification) is str:
            match = re.match(r'(\d+)[xX]?')
            if match is not None:
                magnification = int(match.group(1))
            else:
                raise ValueError('magnification must either be an integer or a string in the format "10x", or "10X", or "10" (without quotes).')
        if magnification not in self._objectives:
            raise IndexError('Specified magnification does not correspond to the magnification offered by any of the available objectives.')
        if magnification != self._objective:
            self._transmit(Packet(self, line=None, cmdCode=22, parameter='{}'.format(self._objectives[magnification].position)))
