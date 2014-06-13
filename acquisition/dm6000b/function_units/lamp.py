# Copyright 2014 WUSTL ZPLAB
# Erik Hvatum (ice.rikh@gmail.com)

import enum
from PyQt5 import QtCore
from acquisition.device import DeviceException
from acquisition.dm6000b.function_unit import FunctionUnit
from acquisition.dm6000b.packet import Packet, InvalidPacketReceivedException, TruncatedPacketReceivedException

class Lamp(FunctionUnit):
    '''We are not using the DM6000B's lamp; however, TL and IL shutter settings belong to the lamp function unit.  Rather
    than create confusion by adding a user visible lamp subdevice, the lamp function unit's shutter state properties are
    available as properties of the associated Dm6000b instance.'''

    _InitPhase = enum.Enum('_InitPhase', 'MinIntensity MaxIntensity Done')

    tlShutterOpenedChanged = QtCore.pyqtSignal(bool)
    ilShutterOpenedChanged = QtCore.pyqtSignal(bool)
    intensityChanged = QtCore.pyqtSignal(int)

    def __init__(self, dm6000b, deviceName='Lamp Function Unit'):
        super().__init__(dm6000b, deviceName, 77)
        self._tlShutterOpened = None
        self._ilShutterOpened = None
        self._minIntensity = None
        self._maxIntensity = None
        self._intensity = None
        self._initPhase = self._InitPhase.MinIntensity
        # So that we don't get confused while initing, unsubscribe from all notification events
        self._transmit(Packet(self, cmdCode=3, parameter='0 0 0 0 0 0'))
        # Enumerate min intensity value; enumeration will continue once this value has been retrieved
        self._transmit(Packet(self, cmdCode=23))

    def __del__(self):
        # Unsubscribe from all events
        self._transmit(Packet(self, cmdCode=3, parameter='0 0 0 0 0 0'))
        FunctionUnit.__del__(self)

    def _postEnumerationInit(self):
        # Subscribe to intensity change and shutter open/close events
        self._transmit(Packet(self, cmdCode=3, parameter='0 1 0 0 1 1'))
        # Get current shutter open/close states
        self._transmit(Packet(self, cmdCode=33))
        # Get current intensity
        self._transmit(Packet(self, cmdCode=21))

    def _processReceivedPacket(self, txPacket, rxPacket):
        if self._initPhase == self._InitPhase.Done:
            self._processReceivedNormalPacket(txPacket, rxPacket)
        else:
            self._processReceivedInitPacket(txPacket, rxPacket)

    def _processReceivedNormalPacket(self, txPacket, rxPacket):
        if rxPacket.statusCode == 0:

            if rxPacket.cmdCode == 33:
                # Shutter state change notification event or response to shutter state query
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
                if self._tlShutterOpened != v:
                    self._tlShutterOpened = v
                    self.tlShutterOpenedChanged.emit(v)
                v = toBool(il, 'IL')
                if self._ilShutterOpened != v:
                    self._ilShutterOpened = v
                    self.ilShutterOpenedChanged.emit(v)

            elif rxPacket.cmdCode == 21:
                # Intensity change notification event or response to intensity query
                intensity = int(rxPacket.parameter)
                if intensity != self._intensity:
                    self._intensity = intensity
                    self.intensityChanged.emit(self._intensity)

    def _processReceivedInitPacket(self, txPacket, rxPacket):
        if rxPacket.statusCode == 0:
            
            if rxPacket.cmdCode == 23:
                # Response to min intensity query
                if self._initPhase != self._InitPhase.MinIntensity:
                    raise DeviceException(self, 'Received data out of order during init.')
                self._minIntensity = int(rxPacket.parameter)
                self._initPhase = self._InitPhase.MaxIntensity
                self._transmit(Packet(self, cmdCode=24))

            elif rxPacket.cmdCode == 24:
                # Response to max intensity query
                if self._initPhase != self._InitPhase.MaxIntensity:
                    raise DeviceException(self, 'Received data out of order during init.')
                self._maxIntensity = int(rxPacket.parameter)
                self._initPhase = self._InitPhase.Done
                self._postEnumerationInit()

        elif rxPacket.cmdCode == 3:
            raise DeviceException(self, 'Failed to register for change notification events.  If you have recently ' +
                                        'upgraded your DM6000B\'s firmware, this probably happened because Leica added ' +
                                        'more events for this function unit, and the number of 0 or 1 values in ' +
                                        'event registration packets (command code 3) must exactly match the number ' +
                                        'of events supported.  Fixing this should just be a matter of adding one more ' +
                                        '" 0" at a time to the parameter string for this function unit\'s cmdCode 3 ' +
                                        'packet constructor calls until it starts working again.')

    def _setShutterOpened(self, idx, opened):
        self._transmit(Packet(self, cmdCode=32, parameter='{} {}'.format(idx, '1' if opened else '0')))

    @QtCore.pyqtProperty(bool, notify=tlShutterOpenedChanged)
    def tlShutterOpened(self):
        return self._tlShutterOpened

    @tlShutterOpened.setter
    def tlShutterOpened(self, tlShutterOpened):
        self._setShutterOpened(0, tlShutterOpened)

    @QtCore.pyqtProperty(bool, notify=ilShutterOpenedChanged)
    def ilShutterOpened(self):
        return self._ilShutterOpened

    @ilShutterOpened.setter
    def ilShutterOpened(self, ilShutterOpened):
        self._setShutterOpened(1, ilShutterOpened)

    @QtCore.pyqtProperty(int)
    def minIntensity(self):
        return self._minIntensity

    @QtCore.pyqtProperty(int)
    def maxIntensity(self):
        return self._maxIntensity

    @QtCore.pyqtProperty(int, notify=intensityChanged)
    def intensity(self):
        return self._intensity

    @intensity.setter
    def intensity(self, intensity):
        if intensity < self._minIntensity or intensity > self._maxIntensity:
            e = 'Intensity must be in the range [{}, {}], which the specified value, {}, is not.'
            raise DeviceException(self, e.format(self._minIntensity, self._maxIntensity, intensity))
        self._transmit(Packet(self, cmdCode=20, parameter=str(intensity)))
