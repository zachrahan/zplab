# Copyright 2014 WUSTL ZPLAB
# Erik Hvatum (ice.rikh@gmail.com)

import copy
import enum
from PyQt5 import QtCore
import re
from acquisition.device import DeviceException
from acquisition.dm6000b.enums import ImmersionOrDry
from acquisition.dm6000b.function_unit import FunctionUnit
from acquisition.dm6000b.packet import Packet, InvalidPacketReceivedException, TruncatedPacketReceivedException

class Objective:
    def __init__(self, pos=None, mag=None, type_=None):
        self.pos = pos
        self.mag = mag
        self.type_ = type_
    def __repr__(self):
        return 'Objective(pos={}, mag={}, type_={})'.format(self.pos, self.mag, self.type_)

class ObjectiveTurret(FunctionUnit):
    '''AKA "nose piece" AKA "revolver" - that rotating bit of hardware to which objectives of various maginifications
    are attached.  This Device is meant to act as a subdevice of Dm6000b and, as such, depends on its parent to send
    requests to the DM6000B and to deliver responses from it.'''

    _ObjectivesInitPhase = enum.Enum('_ObjectivesInitPhase', 'GetMin GetMax Enumerate Done')

    objectiveTurretMovingChanged = QtCore.pyqtSignal(bool)
    posChanged = QtCore.pyqtSignal()
    magChanged = QtCore.pyqtSignal()
    immersionOrDryChanged = QtCore.pyqtSignal(ImmersionOrDry)

    def __init__(self, dm6000b, deviceName='Objective Turret Function Unit'):
        super().__init__(dm6000b, deviceName, 76)
        # So that we don't get confused while initing, unsubscribe from all of the objective turret function unit change events
        self._transmit(Packet(self, cmdCode=3, parameter='0 0 0 0 0 0 0 0 0 0'))
        self._pos = None
        # Contains one Objective instance for each turret position at the index corresponding to its position.  Leica uses
        # the convention that position index zero is a special value indicating that the turret is between positions, and counts
        # usable positions from 1.  Therefore, index always 0 corresponds to a null objective.
        self._objectivesByPos = [Objective(0, None, None)]
        # Hash of magnification values to objectives with those magnfications (each value in the dict being a list of Objectives)
        self._objectivesByMag = {}
        self._immersionOrDry = None
        self._moving = None
        self._objectiveMinPos = None
        self._objectiveMaxPos = None
        self._objectivesInitPhase = self._ObjectivesInitPhase.GetMin
        # Begin scanning objectives by requesting min objective index (scanning will continue once this value is retrieved)
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
        # Subscribe to change events for: turret in motion, immersion or dry state change
        self._transmit(Packet(self, cmdCode=3, parameter='1 0 0 0 0 0 1 0 0 0'))

    def _processReceivedPacket(self, txPacket, rxPacket):
        if self._objectivesInitPhase == self._ObjectivesInitPhase.Done:
            self._processReceivedNormalPacket(txPacket, rxPacket)
        else:
            self._processReceivedInitPacket(txPacket, rxPacket)

    def _processReceivedNormalPacket(self, txPacket, rxPacket):
        if rxPacket.statusCode == 0:

            if rxPacket.cmdCode == 4:
                # "Is objective turret in motion" event or response.  (As in, whether the scope is switching between objective
                # turret positions, not whether the turret is moving because the scope itself is moving due to earthquake or
                # perhaps a viking hoisting the scope into a long boat.  We'd have to mount some accelerometers to the scope
                # stand if we wanted that information.)
                vs = rxPacket.parameter.split(' ')
                vs = [int(v) for v in vs]
                if vs == [1, 1, 1, 0] or vs == [1, 0, 0, 1]:
                    moving = True
                else:
                    moving = False

                if moving != self._moving:
                    self._moving = moving
                    if moving:
                        self._pos = 0
                        self.posChanged.emit()
                        self._mag = None
                        self.magChanged.emit()
                    else:
                        # Get new position
                        self._transmit(Packet(self, cmdCode=23))
                    self.objectiveTurretMovingChanged.emit(self._moving)

            elif rxPacket.cmdCode == 28:
                # Immersion or dry mode query change notification event or response to query
                if rxPacket.parameter == 'D':
                    immersionOrDry = ImmersionOrDry.Dry
                elif rxPacket.parameter == 'I':
                    immersionOrDry = ImmersionOrDry.Immersion
                else:
                    raise InvalidPacketReceivedException(self, 'Parameter must be "D" or "I", not "{}".'.format(rxPacket.parameter))

                if immersionOrDry != self._immersionOrDry:
                    self._immersionOrDry = immersionOrDry
                    self.immersionOrDryChanged.emit(self._immersionOrDry)

            elif rxPacket.cmdCode == 23:
                # Response to position query
                pos = int(rxPacket.parameter)
                self._pos = pos
                self._mag = self._objectivesByPos[self._pos].mag
                self.posChanged.emit()
                self.magChanged.emit()

        elif rxPacket.statusCode == 3:
            if rxPacket.cmdCode == 22:
                # Scope rejected turret position change command
                pos = int(txPacket.parameter)
                raise DeviceException(self, 'Failed to switch to {}x objective at position {}.  '.format(self._objectivesByPos[pos].mag, pos) +
                                            'The cause of this is often that the specified objective is not compatible with the current immersionOrDry setting.  '
                                            'Before switching to an immersion objective, set immersionOrDry = "I", and for standard objectives, "D".')

    def _processReceivedInitPacket(self, txPacket, rxPacket):
        if rxPacket.statusCode == 0:

            if rxPacket.cmdCode == 38:
                # Response to minimum objective position index query
                if self._objectivesInitPhase != self._ObjectivesInitPhase.GetMin:
                    raise DeviceException(self, 'Received data out of order during init.')
                self._objectiveMinPos = int(rxPacket.parameter)
                if self._objectiveMinPos != 1:
                    raise DeviceException(self, 'Received unexpected value for objective turret minimum position (expected 1, got {}).'.format(self._objectiveMinPos))
                self._objectivesInitPhase = self._ObjectivesInitPhase.GetMax
                self._transmit(Packet(self, cmdCode=39))

            elif rxPacket.cmdCode == 39:
                # Response to maximum objective position index query
                if self._objectivesInitPhase != self._ObjectivesInitPhase.GetMax:
                    raise DeviceException(self, 'Received data out of order during init.')
                self._objectiveMaxPos = int(rxPacket.parameter)
                if self._objectiveMaxPos < self._objectiveMinPos:
                    raise DeviceException(self, 'Received impossible value for maximum position (expected value >= {}, got {}).'.format(self._objectiveMinPos, self._objectiveMaxPos))
                for pos in range(self._objectiveMinPos, self._objectiveMaxPos + 1):
                    self._objectivesByPos.append(Objective(pos))
                self._objectivesInitPhase = self._ObjectivesInitPhase.Enumerate
                self._objectivePositionsAwaitingInitResponse = {p:[True, True] for p in range(self._objectiveMinPos, self._objectiveMaxPos + 1)}
                for p in self._objectivePositionsAwaitingInitResponse.keys():
                    self._transmit(Packet(self, cmdCode=33, parameter='{} 1'.format(p)))
                    self._transmit(Packet(self, cmdCode=33, parameter='{} 5'.format(p)))

            elif rxPacket.cmdCode == 33:
                # Reponse to objective parameter query...
                if self._objectivesInitPhase != self._ObjectivesInitPhase.Enumerate:
                    raise DeviceException(self, 'Received data out of order during init.')
                vs = rxPacket.parameter.split(' ')
                pos = int(vs[0])
                par = int(vs[1])
                awaiting = self._objectivePositionsAwaitingInitResponse[pos]
                objective = self._objectivesByPos[pos]
                if par == 1:
                    # ... for objective maginifacation parameter
                    if not awaiting[0]:
                        raise DeviceException(self, 'Received duplicate response for objective magnification.')
                    if vs[2] != '-':
                        # "-" indicates empty objective position.  magnification values for empty objectives remain None
                        # as a result of the if statement containing this comment.
                        objective.mag = int(vs[2])
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
                    del self._objectivePositionsAwaitingInitResponse[pos]

                # In retrospect, this is more complex than necessary and would have been better implemented as
                # two init steps, one for each value to be enumerated, rather than as a combined step retrieving
                # both magnification and type.  It does work, however.
                if len(self._objectivePositionsAwaitingInitResponse) == 0:
                    for objective in self._objectivesByPos:
                        if objective.mag is not None: # Skip empty positions
                            if objective.mag in self._objectivesByMag:
                                self._objectivesByMag[objective.mag].append(objective)
                            else:
                                self._objectivesByMag[objective.mag] = [objective]
                    self._objectivesInitPhase = self._ObjectivesInitPhase.Done
                    del self._objectivePositionsAwaitingInitResponse
                    self._postEnumerationInit()

    @QtCore.pyqtProperty(bool, notify=objectiveTurretMovingChanged)
    def objectiveTurretMoving(self):
        return self._moving

    @QtCore.pyqtProperty(int, notify=posChanged)
    def pos(self):
        return self._pos

    @pos.setter
    def pos(self, pos):
        if pos < self._objectiveMinPos or pos > self._objectiveMaxPos:
            raise ValueError('pos must be an integer in the range [{}, {}].'.format(self._objectiveMinPos, self._objectiveMaxPos))
        self._transmit(Packet(self, line=None, cmdCode=22, parameter=str(pos)))

    @QtCore.pyqtProperty(float, notify=magChanged)
    def mag(self):
        return self._objectivesByPos[self._pos].mag

    @mag.setter
    def mag(self, mag):
        if type(mag) is str:
            match = re.match(r'(\d+|\d+\.\d+|\.\d+)[xX]?')
            if match is not None:
                mag = float(match.group(1))
            else:
                raise ValueError('mag must either be a numeric value or a string in the format "10x", or "10X", or "10" (without quotes).')
        if mag not in self._objectivesByMag:
            raise IndexError('Specified magnification does not correspond to the magnification offered by any of the available objectives.')
        magObjectives = self._objectivesByMag[mag]
        if len(magObjectives) > 1:
            poss = ', '.join([str(objective.pos) for objective in magObjectives])
            raise IndexError('Specified magnification ({}x) is ambiguous (objectives at positions {} have this magnification).'.format(mag, poss))
        pos = magObjectives[0].pos
        if pos != self._pos:
            self._transmit(Packet(self, line=None, cmdCode=22, parameter='{}'.format(pos)))

    @QtCore.pyqtProperty(ImmersionOrDry, notify=immersionOrDryChanged)
    def immersionOrDry(self):
        return self._immersionOrDry

    @immersionOrDry.setter
    def immersionOrDry(self, immersionOrDry):
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

    @QtCore.pyqtProperty(dict)
    def objectives(self):
        return copy.deepcopy(self._objectivesByPos)
