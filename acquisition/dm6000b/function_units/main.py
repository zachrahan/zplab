# Copyright 2014 WUSTL ZPLAB
# Erik Hvatum (ice.rikh@gmail.com)

from PyQt5 import QtCore
from acquisition.device import DeviceException
from acquisition.dm6000b.enums import Method
from acquisition.dm6000b.function_unit import FunctionUnit
from acquisition.dm6000b.packet import Packet, InvalidPacketReceivedException, TruncatedPacketReceivedException

class MainFunctionUnit(FunctionUnit):
    '''Dm6000b can't inherit from both ThreadedDevice and FunctionUnit.  However, a user will expect to find properties for
    the scope "main function unit" as attributes of Dm6000b directly, not as attributes of Dm6000b.mainUnit or somesuch.
    _Dm6000bWorker could route main function unit packets back to its Dm6000b instance, but then
    FunctionUnit._processReceivedPacket and every other aspect of FunctionUnit would need to be reimplemented as a methods
    of Dm6000b, which would be redundant and very confusing.

    Instead, a FunctionUnit _MainFunctionUnit is made that stores all its user accessible properties in its associated
    Dm6000b instance, where they are easily found by the user.'''

    activeMethodChanged = QtCore.pyqtSignal(Method)

    def __init__(self, dm6000b, deviceName='Main Function Unit'):
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
                # Response to available methods query
                methods = []
                for method in Method:
                    s = rxPacket.parameter[-method.value]
                    if s == '0':
                        # Method not supported
                        pass
                    elif s == '1':
                        # Method supported
                        methods.append(method)
                    else:
                        e = 'Method supported element must be either "0" or "1", not "{}".'
                        raise InvalidPacketReceivedException(self, e.format(s))
                self._methods = frozenset(methods)
            elif rxPacket.cmdCode == 28:
                # Current method changed notification event or response to current method query
                self._activeMethod = Method(int(rxPacket.parameter))
                self.dm6000b.activeMethodChanged.emit(self._activeMethod)

    def _setActiveMethod(self, method):
        self._transmit(Packet(self, line=None, cmdCode=29, parameter='{} x'.format(method.value)))

    @QtCore.pyqtProperty(frozenset)
    def methods(self):
        '''Frozenset containing supported methods.  For example, to see if "IL DIC" is supported, do "dm6000b.Methods.IL_DIC
        in dm6000b.methods.'''
        return self._methods

    @QtCore.pyqtProperty(dict)
    def methodsAsDict(self):
        '''The same as the methods property, except a dict of "Method enum value -> is supported bool" is returned.'''
        return {method : self._methods[method] for method in Method}

    @QtCore.pyqtProperty(Method, notify=activeMethodChanged)
    def activeMethod(self):
        return self._activeMethod

    @activeMethod.setter
    def activeMethod(self, activeMethod):
        self._setActiveMethod(activeMethod)
