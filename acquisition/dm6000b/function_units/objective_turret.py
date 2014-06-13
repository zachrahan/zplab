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

class ObjectiveTurret(FunctionUnit):
    '''AKA "nose piece" AKA "revolver" - that rotating bit of hardware to which objectives of various maginifications
    are attached.  This Device is meant to act as a subdevice of Dm6000b and, as such, depends on its parent to send
    requests to the DM6000B and to deliver responses from it.'''

    _ObjectivesInitPhase = enum.Enum('_ObjectivesInitPhase', 'GetMin GetMax Enumerate Done')

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
        # Get current objective magnification
        self._transmit(Packet(self, cmdCode=33, parameter='a 1'))
        # Get current immsersion or dry state
        self._transmit(Packet(self, cmdCode=28))
        # Get current objective movement state
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
                # Response to "is objective turret in motion" query.  (As in, whether the scope is switching between objective
                # turret positions, not whether the turret is moving because the scope itself is moving due to earthquake or
                # perhaps a viking hoisting the scope into a long boat.  We'd have to mount some accelerometers to the scope
                # stand if we wanted that information.)
                vs = rxPacket.parameter.split(' ')
                if vs[2] == '1' and vs[3] == '0':
                    moving = False
                elif vs[2] == '0' and vs[3] == '1':
                    moving = True
                else:
                    raise InvalidPacketReceivedException(self, 'Final two parameter values must be "0 1" or "1 0", not "{} {}".'.format(vs[2], vs[3]))

                if moving != self._moving:
                    self._moving = moving
                    self.objectiveTurretMovingChanged.emit(self._moving)

            elif rxPacket.cmdCode == 28:
                # Response to scope immersion or dry mode query
                if rxPacket.parameter == 'D':
                    immersionOrDry = ImmersionOrDry.Dry
                elif rxPacket.parameter == 'I':
                    immersionOrDry = ImmersionOrDry.Immersion
                else:
                    raise InvalidPacketReceivedException(self, 'Parameter must be "D" or "I", not "{}".'.format(rxPacket.parameter))

                if immersionOrDry != self._immersionOrDry:
                    self._immersionOrDry = immersionOrDry
                    self.immersionOrDryChanged.emit(self._immersionOrDry)

            elif rxPacket.cmdCode == 33:
                # Current magnification changed notification event or response to current maginifaction query
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
                        self.objectiveChanged.emit(self._objective)
                else:
                    raise DeviceException(self, 'Received extraneous (non-requested) objective parameter data.')

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
                self._objectivesInitPhase = self._ObjectivesInitPhase.Enumerate
                self._objectivePositionsAwaitingInitResponse = {p:[True, True] for p in range(self._objectiveMinPosition, self._objectiveMaxPosition+1)}
                self._objectivesByPosition = {p:Objective() for p in range(self._objectiveMinPosition, self._objectiveMaxPosition+1)}
                for p in self._objectivePositionsAwaitingInitResponse.keys():
                    self._transmit(Packet(self, cmdCode=33, parameter='{} 1'.format(p)))
                    self._transmit(Packet(self, cmdCode=33, parameter='{} 5'.format(p)))

            elif rxPacket.cmdCode == 33:
                # Reponse to objective parameter query...
                if self._objectivesInitPhase != self._ObjectivesInitPhase.Enumerate:
                    raise DeviceException(self, 'Received data out of order during init.')
                vs = rxPacket.parameter.split(' ')
                position = int(vs[0])
                par = int(vs[1])
                awaiting = self._objectivePositionsAwaitingInitResponse[position]
                objective = self._objectivesByPosition[position]
                if par == 1:
                    # ... for objective maginifacation parameter
                    if not awaiting[0]:
                        raise DeviceException(self, 'Received duplicate response for objective magnification.')
                    objective.position = position
                    if vs[2] != '-':
                        # "-" indicates empty objective position.  magnification values for empty objectives remain None
                        # as a result of the if statement containing this comment.
                        objective.magnification = int(vs[2])
                    awaiting[0] = False
                elif par == 5:
                    # ... for objective type parameter (eg, O for oil, D for dry, and a zoo of other exotic types too great
                    # in their multitude to bother representing with an enum)
                    if not awaiting[1]:
                        raise DeviceException(self, 'Received duplicate response for objective type.')
                    objective.type_ = vs[2]
                    awaiting[1] = False
                else:
                    # ... that was never made
                    raise DeviceException(self, 'Received extraneous (non-requested) objective parameter data.')

                if not any(awaiting):
                    del self._objectivePositionsAwaitingInitResponse[position]

                # In retrospect, this is more complex than necessary and would have been better implemented as
                # two init steps, one for each value to be enumerated, rather than as a combined step retrieving
                # both magnification and type.  It does work, however.
                if len(self._objectivePositionsAwaitingInitResponse) == 0:
                    for position, objective in self._objectivesByPosition.items():
                        if objective.magnification is not None: # Skip empty positions
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

    def _setImmersionOrDry(self, immersionOrDry):
        if type(immersionOrDry) is str:
            if immersionOrDry in ('d', 'D'):
                v = ImmersionOrDry.Dry
            elif immersionOrDry in ('i', 'I'):
                v = ImmersionOrDry.Immersion
            else:
                raise ValueError('When provided as a string, the immersionOrDry parameter must be "D" or "I" (without quotes), not "{}".'.format(immersionOrDry))
        else:
            v = immersionOrDry

        if v != self._immersionOrDry:
            if v == ImmersionOrDry.Dry:
                parameter = 'D'
            elif v == ImmersionOrDry.Immersion:
                parameter = 'I'
            else:
                e = 'Unsupported value "{0}" specified for immersionOrDry.  This function only knows about "{1}" and "{2}".  If it needs to support '
                e+= '"{0}", then it has to be updated or otherwise modified to do so....  But... Do you really want to immerse your objective in '
                e+= '"{0}"?  Really really?  Does that make sense as a thing that would happen to an objective?  Being immersed in "{0}"?'
                raise DeviceException(self, e.format(v, ImmersionOrDry.Dry, ImmersionOrDry.Immersion))
            self._transmit(Packet(self, cmdCode=27, parameter=parameter))

    @QtCore.pyqtProperty(ImmersionOrDry, notify=immersionOrDryChanged)
    def immersionOrDry(self):
        return self._immersionOrDry

    @immersionOrDry.setter
    def immersionOrDry(self, immersionOrDry):
        self._setImmersionOrDry(immersionOrDry)

    @QtCore.pyqtProperty(bool, notify=objectiveTurretMovingChanged)
    def objectiveTurretMoving(self):
        return self._moving

    @QtCore.pyqtProperty(set)
    def objectives(self):
        return set(self._objectives.keys())

    @QtCore.pyqtProperty(dict)
    def objectivesDetails(self):
        return copy.deepcopy(self._objectives)

    @QtCore.pyqtProperty(int, notify=objectiveChanged)
    def objective(self):
        return self._objective

    @objective.setter
    def objective(self, magnification):
        self._setObjective(magnification)
