# Copyright 2014 WUSTL ZPLAB
# Erik Hvatum (ice.rikh@gmail.com)

import copy
import enum
from PyQt5 import QtCore
from acquisition.device import DeviceException
from acquisition.dm6000b.enums import Method
from acquisition.dm6000b.function_unit import FunctionUnit
from acquisition.dm6000b.packet import Packet, InvalidPacketReceivedException, TruncatedPacketReceivedException

class Cube:
    def __init__(self, position=None, name=None, methods=None):
        self.position = position
        self.name = name
        self.methods = methods
    def __repr__(self):
        return 'Cube(position={}, name={}, methods={})'.format(self.position, self.name, self.methods)

class CubeTurret(FunctionUnit):
    _InitPhase = enum.Enum('_InitPhase', 'MinPos MaxPos EnumerateNames EnumerateMethods Done')

    cubeChanged = QtCore.pyqtSignal(str)

    def __init__(self, dm6000b, deviceName='Cube Turret'):
        super().__init__(dm6000b, deviceName, 78)
        # So that we don't get confused while initing, unsubscribe from cube change notification events
        self._transmit(Packet(self, cmdCode=3, parameter='0'))
        # Begin scanning cubes by requesting min cube pos/index (scanning will continue once this value is retrieved)
        self._cube = None
        # cube names -> Cube instances
        self._cubes = {}
        # cube positions -> cube names
        self._positionCubeNames = {}
        self._initPhase = self._InitPhase.MinPos
        self._transmit(Packet(self, cmdCode=31))

    def __del__(self):
        # Unsubscribe from cube change event
        self._transmit(Packet(self, cmdCode=3, parameter='0'))
        FunctionUnit.__del__(self)

    def _postEnumerationInit(self):
        # Get current position
        self._transmit(Packet(self, cmdCode=23))
        # Subscribe to cube change notification events
        self._transmit(Packet(self, cmdCode=3, parameter='1'))

    def _processReceivedPacket(self, txPacket, rxPacket):
        if self._initPhase == self._InitPhase.Done:
            self._processReceivedNormalPacket(txPacket, rxPacket)
        else:
            self._processReceivedInitPacket(txPacket, rxPacket)

    def _processReceivedNormalPacket(self, txPacket, rxPacket):
        if rxPacket.cmdCode == 22:
            # Response to switch cube command
            if rxPacket.statusCode != 0:
                reqCube = self._cubes[self._positionCubeNames[int(txPacket.parameter)]]
                e = 'Failed to switch to {0} cube because this cube is not compatible with the current method ({1}).  '
                e+= 'Methods supported by {0}: {2}.'
                raise DeviceException(self, e.format(reqCube.name, repr(self.dm6000b.activeMethod), reqCube.methods))
        elif rxPacket.cmdCode == 23:
            # Current cube changed notification event or response to get current pos query
            if rxPacket.statusCode == 0:
                pos = int(rxPacket.parameter.split()[0])
                if pos not in self._positionCubeNames:
                    # Current cube position is empty
                    cube = None
                else:
                    cube = self._positionCubeNames[pos]

                if cube != self._cube:
                    self._cube = cube
                    self.cubeChanged.emit(self._cube)

    def _processReceivedInitPacket(self, txPacket, rxPacket):
        if rxPacket.statusCode == 0:

            if rxPacket.cmdCode == 31:
                # Response to turret minimum position query
                if self._initPhase != self._InitPhase.MinPos:
                    raise DeviceException(self, 'Received data out of order during init.')
                self._minPos = int(rxPacket.parameter)
                self._initPhase = self._InitPhase.MaxPos
                self._transmit(Packet(self, cmdCode=32))

            elif rxPacket.cmdCode == 32:
                # Response to turret maximum position query
                if self._initPhase != self._InitPhase.MaxPos:
                    raise DeviceException(self, 'Received data out of order during init.')
                self._maxPos = int(rxPacket.parameter)
                self._positionsAwaitingInitResponse = set(range(self._minPos, self._maxPos+1))
                self._initPhase = self._InitPhase.EnumerateNames
                # Query names of all cubes
                for p in self._positionsAwaitingInitResponse:
                    self._transmit(Packet(self, cmdCode=27, parameter=str(p)))

            elif rxPacket.cmdCode == 27:
                # Response to cube name query
                if self._initPhase != self._InitPhase.EnumerateNames:
                    raise DeviceException(self, 'Received data out of order during init.')
                vs = rxPacket.parameter.split() # Called with no parameter so that excess whitespace is thrown away
                if len(vs) not in (1, 2):
                    InvalidPacketReceivedException(self, 'Response to cube name query must contain either one or two ' +
                                                         'parameters, not {}.'.format(len(vs)))
                # All of our filter cube positions are occupied, and position occupation is known to the scope
                # from stored user settings.  Causing the scope to regard a position as empty for testing purposes
                # is therefore not very easy.  So, it has not been verified that the following if statement
                # condition and cmdCode 27 alternate status code check are sufficient catching empty positions.
                if len(vs) == 1 or vs[1] == '-':
                    # Empty position
                    self._positionsAwaitingInitResponse.remove(int(vs[0]))
                else:
                    # Occupied position
                    pos = int(vs[0])
                    name = vs[1]
                    if pos not in self._positionsAwaitingInitResponse:
                        e = 'Received duplicate response for turret position {} cube name query.'
                        raise InvalidPacketReceivedException(self, e.format(pos))
                    self._positionsAwaitingInitResponse.remove(pos)
                    if name in self._cubes:
                        e = 'More than one filter cube is named "{}".  Because this application identifies filter cubes by '
                        e+= 'name, duplicate filter cube names are not supported.'
                        raise DeviceException(self, e.format(name))
                    self._cubes[name] = Cube(pos, name)
                    self._positionCubeNames[pos] = name

                if len(self._positionsAwaitingInitResponse) == 0:
                    self._positionsAwaitingInitResponse = set(self._positionCubeNames.keys())
                    self._initPhase = self._InitPhase.EnumerateMethods
                    # Query methods of all cubes
                    for p in self._positionsAwaitingInitResponse:
                        self._transmit(Packet(self, cmdCode=30, parameter=str(p)))

            elif rxPacket.cmdCode == 30:
                # Response to cube methods query
                if self._initPhase != self._InitPhase.EnumerateMethods:
                    raise DeviceException(self, 'Received data out of order during init.')
                vs = rxPacket.parameter.split(' ')
                pos = int(vs[0])
                if pos not in self._positionsAwaitingInitResponse:
                    e = 'Received duplicate response for turret position {} methods query.'
                    raise InvalidPacketReceivedException(self, e.format(pos))
                self._positionsAwaitingInitResponse.remove(pos)
                cube = self._cubes[self._positionCubeNames[pos]]
                methodsStr = vs[1]
                methods = []
                for method in Method:
                    s = methodsStr[-method.value]
                    if s == '0':
                        # Method not supported
                        pass
                    elif s == '1':
                        # Method supported
                        methods.append(method)
                    else:
                        e = 'Method supported element must be either "0" or "1", not "{}".'
                        raise InvalidPacketReceivedException(self, e.format(s))
                cube.methods = frozenset(methods)
                if len(self._positionsAwaitingInitResponse) == 0:
                    del self._positionsAwaitingInitResponse
                    self._initPhase = self._InitPhase.Done
                    self._postEnumerationInit()


        elif rxPacket.cmdCode == 27:
            # The "alternate status code check" referred to above
            raise DeviceException(self, 'Cube name query failed.  If you have an empty position in your cube turret ' +
                                        'AKA IL Turret AKA filter turret, then this error probably  occurred because this ' +
                                        'application was written without complete knowledge of how the scope behaves in ' +
                                        'this circumstance.  Correcting this may be a matter of uncommenting the line ' +
                                        'immediately following the site from which this exception was thrown and ' +
                                        'deleting or commenting out the raise statement that threw this exception.')
#           self._positionsAwaitingInitResponse.remove(int(txPacket.parameter.split()[0]))

    @QtCore.pyqtProperty(str, notify=cubeChanged)
    def cube(self):
        return self._cube

    @cube.setter
    def cube(self, cube):
        if cube not in self._cubes:
            raise ValueError('There is no cube named "{}" in the cube turret.'.format(cube))
        if cube != self._cube:
            self._transmit(Packet(self, cmdCode=22, parameter=str(self._cubes[cube].position)))

    @QtCore.pyqtProperty(set)
    def cubes(self):
        return set(self._cubes.keys())

    @QtCore.pyqtProperty(dict)
    def cubesDetails(self):
        return copy.deepcopy(self._cubes)
