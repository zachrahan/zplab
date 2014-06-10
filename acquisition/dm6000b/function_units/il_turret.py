# Copyright 2014 WUSTL ZPLAB
# Erik Hvatum (ice.rikh@gmail.com)

import enum
from PyQt5 import QtCore
import re
from acquisition.device import DeviceException
from acquisition.dm6000b.enums import ImmersionOrDry
from acquisition.dm6000b.function_unit import FunctionUnit
from acquisition.dm6000b.packet import Packet, InvalidPacketReceivedException, TruncatedPacketReceivedException

class FilterCube:
    def __init__(self, position=None, name=None, methods=None):
        self.position = position
        self.name = name
        self.methods = methods
    def __repr__(self):
        return 'FilterCube(position={}, name={}, methods={})'.format(self.position, self.name, self.methods)

class IlTurret(FunctionUnit):
    _InitPhase = enum.Enum('_InitPhase', 'MinPos MaxPos EnumerateNames EnumerateMethods Done')

    def __init__(self, dm6000b, deviceName='IL Turret'):
        super().__init__(dm6000b, deviceName, 78)
        # So that we don't get confused while initing, unsubscribe from cube change notifications
        self._transmit(Packet(self, cmdCode=3, parameter='0'))
        # Begin scanning cubes by requesting min cube pos/index (scanning will continue once this value is retrieved)
        self._cube = None
        self._cubes = {}
        self._positionCubeNames = {}
        self._transmit(Packet(self, cmdCode=31))

    def __del__(self):
        # Unsubscribe from cube change event
        self._transmit(Packet(self, cmdCode=3, parameter='0'))
        FunctionUnit.__del__(self)

    def _postEnumerationInit(self):
        pass
