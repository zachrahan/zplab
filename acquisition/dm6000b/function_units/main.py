# Copyright 2014 WUSTL ZPLAB
# Erik Hvatum (ice.rikh@gmail.com)

from PyQt5 import QtCore
from acquisition.device import DeviceException
from acquisition.dm6000b.enums import Method
from acquisition.dm6000b.function_unit import FunctionUnit
from acquisition.dm6000b.packet import Packet, InvalidPacketReceivedException, TruncatedPacketReceivedException

class _MainFunctionUnit(FunctionUnit):
    '''Dm6000b can't inherit from both ThreadedDevice and FunctionUnit.  However, a user will expect to find properties for
    the scope "main function unit" as attributes of Dm6000b directly, not as attributes of Dm6000b.mainUnit or somesuch.
    _Dm6000bWorker could route main function unit packets back to its Dm6000b instance, but then
    FunctionUnit._processReceivedPacket and every other aspect of FunctionUnit would need to be reimplemented as a methods
    of Dm6000b, which would be redundant and very confusing.

    Instead, a FunctionUnit _MainFunctionUnit is made that stores all its user accessible properties in its associated
    Dm6000b instance, where they are easily found by the user.'''

    def __init__(self, dm6000b, deviceName='hidden Main Function Unit - properties proxied to Dm6000b'):
        super().__init__(dm6000b, deviceName, 70)
        self.dm6000b._methods = None
        # Get available methods
        self._methods = None
        self._transmit(Packet(self, line=None, cmdCode=26))
        # Get current method
        self._activeMethod = None
        self._transmit(Packet(self, line=None, cmdCode=28))
        # Subscribe to method change events
        self._transmit(Packet(self, line=None, cmdCode=3, parameter='1 0 0 0 0 0 0 0'))

    def _processReceivedPacket(self, txPacket, rxPacket):
        if rxPacket.statusCode == 0:
            if rxPacket.cmdCode == 26:
                methods = []
                for method in Method:
                    s = rxPacket.parameter[-method.value]
                    if s == '0':
                        methods.append(False)
                    elif s == '1':
                        methods.append(True)
                    else:
                        raise InvalidPacketReceivedException(self, 'Method supported element must be either "0" or "1", not "{}".'.format(s))
                self._methods = methods
            elif rxPacket.cmdCode == 28:
                self._activeMethod = Method(int(rxPacket.parameter))
                self.dm6000b.activeMethodChanged.emit(self._activeMethod)

    def _setActiveMethod(self, method):
        self._transmit(Packet(self, line=None, cmdCode=29, parameter='{} x'.format(method.value)))
