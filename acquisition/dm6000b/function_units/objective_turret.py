# Copyright 2014 WUSTL ZPLAB
# Erik Hvatum (ice.rikh@gmail.com)

from PyQt5 import QtCore
from acquisition.device import DeviceException
from acquisition.dm6000b.function_unit import FunctionUnit
from acquisition.dm6000b.packet import Packet, InvalidPacketReceivedException, TruncatedPacketReceivedException

class ObjectiveTurret(FunctionUnit):
    '''AKA "nose piece" AKA "revolver" - that rotating bit of hardware to which objectives of various maginifications
    are attached.  This Device is meant to act as a subdevice of Dm6000b and, as such, depends on its parent to send
    requests to the DM6000B and to deliver responses from it.'''
    class Objective:
        def __init__(self):
            self.empty = None
            self.magnification = None
            self.articleNumber = None
            self.methods = None
            self.type_ = None
            self.parfocalityLevelingCounts = None
            self.lowerZCounts = None
            self.immserseZCounts = None
            self.zStepIncrement = None
            self.tlIlluminationFieldDiaphramValue = None
            self.tlAperatureFieldDiaphramValue = None
            self.ilIlluminationFieldDiaphramValue = None
            self.ilAperatureFieldDiaphramValue = None
            self.lampIntensity = 
