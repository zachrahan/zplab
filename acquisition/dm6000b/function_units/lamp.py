# Copyright 2014 WUSTL ZPLAB
# Erik Hvatum (ice.rikh@gmail.com)

from PyQt5 import QtCore
from acquisition.device import DeviceException
from acquisition.dm6000b.function_unit import FunctionUnit
from acquisition.dm6000b.packet import Packet, InvalidPacketReceivedException, TruncatedPacketReceivedException

class _Lamp(FunctionUnit):
    '''We are not using the DM6000B's lamp; however, TL and IL shutter settings belong to the lamp function unit.  Rather
    than create confusion by adding a user visible lamp subdevice, the lamp function unit's shutter state properties are
    available as properties of the associated Dm6000b instance.'''

    def __init__(self, dm6000b, deviceName='hidden Lamp Function Unit - properties proxied to Dm6000b'):
        super().__init__(dm6000b, deviceName, 77)
        self.dm6000b._tlShutterOpened = None
        self.dm6000b._ilShutterOpened = None
        # Subscribe to shutter open/close events
        self._transmit(Packet(self, line=None, cmdCode=3, parameter='0 0 0 0 1 1'))
        # Get current shutter open/close states
        self._transmit(Packet(self, line=None, cmdCode=33))

    def __del__(self):
        # Unsubscribe from all events
        self._transmit(Packet(self, line=None, cmdCode=3, parameter='0 0 0 0 0 0'))
        FunctionUnit.__del__(self)

    def _processReceivedPacket(self, txPacket, rxPacket):
        if rxPacket.statusCode == 0:
            if rxPacket.cmdCode == 33:
                tl, il = rxPacket.parameter.split(' ')
                def toBool(s, n):
                    if s == '0':
                        return False
                    elif s == '1':
                        return True
                    elif s == '-1':
                        print('Your "{}" reports that the {} shutter has encountered a problem.  In fact, '.format(self.dm6000b.deviceName, n) +
                              'the microscope doesn\'t know whether that shutter is even open.  This is generally not an ' +
                              'error you want to be having.  So, I\'m going to go ahead and exit, while you dutifully ' +
                              'attend to your broken microscope, dear user.', sys.stderr)
                        sys.exit(-1)
                    else:
                        raise InvalidPacketReceivedException(self, 'Shutter state value must be either "0", "1", or "-1", but not "{}".'.format(s))
                v = toBool(tl, 'TL')
                if self.dm6000b._tlShutterOpened != v:
                    self.dm6000b._tlShutterOpened = v
                    self.dm6000b.tlShutterOpenedChanged.emit(v)
                v = toBool(il, 'IL')
                if self.dm6000b._ilShutterOpened != v:
                    self.dm6000b._ilShutterOpened = v
                    self.dm6000b.ilShutterOpenedChanged.emit(v)

    def _setShutterOpened(self, idx, opened):
        self._transmit(Packet(self, line=None, cmdCode=32, parameter='{} {}'.format(idx, '1' if opened else '0')))
