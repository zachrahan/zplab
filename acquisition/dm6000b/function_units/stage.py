# Copyright 2014 WUSTL ZPLAB
# Erik Hvatum (ice.rikh@gmail.com)

from PyQt5 import QtCore
import numpy
import re
import sys
from acquisition.device import DeviceException
from acquisition.dm6000b.function_unit import FunctionUnit
from acquisition.dm6000b.packet import Packet, InvalidPacketReceivedException, TruncatedPacketReceivedException

class Stage(FunctionUnit):
    '''This Device represents an interface to any of three separate DM6000B "function units" (in Leica terminology).
    These are the Z-DRIVE (function code 71), X-AXIS (72), Y-AXIS (73).  This Device is meant to act as a subdevice of
    Dm6000b and, as such, depends on its parent to send requests to the DM6000B and to deliver responses from it.'''

    posChanged = QtCore.pyqtSignal(float)
    movingChanged = QtCore.pyqtSignal(bool)

    def __init__(self, dm6000b, deviceName, funitCode, factor):
        super().__init__(dm6000b, deviceName, funitCode)
        self._factor = factor
        self._pos = numpy.nan
        self.refreshPos()
        self._moving = None
        # Used to delay signaling of movingChanged(False) until new stage position has been retrieved
        self._didStop = False
        self._transmit(Packet(self, cmdCode=4))
        # Subscribe to stage movement started/stopped change events
        self._transmit(Packet(self, cmdCode=3, parameter='1 0 0 0 0 0 0 0 0'))

    def __del__(self):
        # Unsubscribe from all stage state change notification events
        self._transmit(Packet(self, cmdCode=3, parameter='0 0 0 0 0 0 0 0 0'))
        FunctionUnit.__del__(self)

    def _processReceivedPacket(self, txPacket, rxPacket):
        if rxPacket.statusCode == 0:

            if rxPacket.cmdCode in (22, 23):
                if rxPacket.cmdCode == 22 and re.match('\s*', rxPacket.parameter) is not None:
                    # Reponse containing command code 22 with empty or whitespace only parameter indicates that a stage
                    # movement request was issued for what is already the stage's current position.
                    self.posChanged.emit(self._pos * self._factor)
                else:
                    self._pos = int(rxPacket.parameter)
                    if self._didStop:
                        self.movingChanged.emit(self._moving)
                        self._didStop = False
                    self.posChanged.emit(self._pos * self._factor)

            elif rxPacket.cmdCode == 4:
                if rxPacket.parameter[0] == '1':
                    moving = True
                elif rxPacket.parameter[0] == '0':
                    moving = False
                else:
                    DeviceError(self, 'First element of parameter list for stage status command response must be either "1" or "0".')

                if moving != self._moving:
                    self._moving = moving
                    if self._moving:
                        # Stage started moving.  The value of our pos property would become ever more wrong while the stage
                        # continues moving.  It would represent the position of the stage when it started moving, but
                        # the potential for a user to instead believe that it always reflects the current state outweighs
                        # that convenience, which, in any case, the user may replicate by simply saving the pos value to
                        # a variable before initiating stage movement.  Instead, pos is set to None to unambiguously
                        # indicate that the pos property's value is undefined while the stage remains in motion.
                        #
                        # Notably, we could subscribe to stage position change notification events and update the pos
                        # value more frequently as a result.  Rather a lot more frequently - we'd receive a deluge of
                        # notifications that would pile up and be emitted simultaneously if the main thread is blocked or
                        # that would severly degrade responsiveness if the main thread is doing anything significant - such as
                        # redrawing GUI elements upon receipt of pos change signals.
                        #
                        # If, for some reason, it is nonetheless essential to know the location of the stage while it moves,
                        # this can be achieved to an extent by calling refreshPos() repeatedly.  Doing so will cause
                        # the pos property to update in the normal fashion, with the caveat that the pos found will
                        # certainly be somewhat out of date even at the time the posChanged signal is emitted, and will
                        # grow ever more out of date until refreshPos() is called again or the stage finishes moving,
                        # at which point pos is always updated.
                        self._pos = numpy.nan
                        self.posChanged.emit(self._pos * self._factor)
                        self.movingChanged.emit(self._moving)
                    else:
                        # Stage stopped moving.  Delay emitting signal indicating this until pos has been updated.
                        self._didStop = True
                        self.refreshPos()

        if rxPacket.statusCode == 3:
            if rxPacket.cmdCode == 22:
                print('Warning: "{}" failed to reach specified location.'.format(self.deviceName), sys.stderr)

    def refreshPos(self):
        self._transmit(Packet(self, line=None, cmdCode=23))

    @QtCore.pyqtProperty(float, notify=posChanged)
    def pos(self):
        return self._pos * self._factor

    @pos.setter
    def pos(self, pos):
        self._transmit(Packet(self, line=None, cmdCode=22, parameter=str(int(pos / self._factor))))

    @QtCore.pyqtProperty(bool, notify=movingChanged)
    def moving(self):
        return self._moving
