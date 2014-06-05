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
    def __init__(self, dm6000b, deviceName, funitCode):
        super().__init__(dm6000b, deviceName, funitCode)

    def _packetReceivedSlot(self, packet):
        print('got response for "{}":  funitCode: {}, cmdCode: {}, parameter: {}'.format(self.deviceName, packet.funitCode, packet.cmdCode, packet.parameter))
