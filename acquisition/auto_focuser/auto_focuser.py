# The MIT License (MIT)
#
# Copyright (c) 2014 WUSTL ZPLAB
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#
# Authors: Erik Hvatum

from enum import Enum
import numpy
from PyQt5 import QtCore
from acquisition.device import Device, DeviceException

class AutoFocuser(Device):
    busyChanged = QtCore.pyqtSignal(bool)
    useMaskChanged = QtCore.pyqtSignal(bool)
    maskChanged = QtCore.pyqtSignal()

    def __init__(self, camera, zDrive, parent=None, deviceName='Auto Focuser'):
        super().__init__(parent, deviceName)
        self._camera = camera
        self._zDrive = zDrive
        self._busy = False
        self._useMask = False
        # PyQt doesn't like assigning None to properties of type object...
        self._mask = object()
        zDrive.movingChanged.connect(self._zDriveMovingChanged)

    def _zDriveMovingChanged(self, moving):
        # If we are currently auto-focusing and the z drive has stopped moving...
        if self._busy and not moving:


    @QtCore.pyqtProperty(object)
    def camera(self):
        return self._camera

    @QtCore.pyqtProperty(object)
    def zDrive(self):
        return self._zDrive

    @QtCore.pyqtProperty(bool, notify=busyChanged)
    def busy(self):
        '''If this property is True, it can only mean that, at the instant the property was read, we were waiting
        for the stage to finish moving.  (Unless you read the property from another thread, in which case its
        meaning is undefined.)'''
        return self._busy

    @QtCore.pyqtProperty(bool, notify=useMaskChanged)
    def useMask(self):
        return self._useMask

    @useMask.setter
    def useMask(self, useMask):
        if useMask != self._useMask:
            if self._busy:
                raise DeviceException('Can not enable/disable focus metric mask while auto focus operation is in progress.')
            self._useMask = useMask
            self.useMaskChanged.emit(self._useMask)

    @QtCore.pyqtProperty(object, notify=maskChanged)
    def mask(self):
        return self._mask

    @mask.setter
    def mask(self, mask):
        if self._busy:
            raise DeviceException('Can not change auto focus mask while auto focus operation is in progress.')
        self._mask = mask
        self.maskChanged.emit()

    def startAutoFocus(self, minZ, maxZ, initialStepCount):
        if self._busy:
            # If an auto focus operation is already in progress, requests to start another are ignored
            return


    def stopAutoFocus(self):
        if not self._busy:
            # If an auto focus operation is not in progress, requests to stop auto focusing are ignored
            return

    def waitForReady(self, timeout=None):
        if self._busy:
            self._waitForSignal(self.busyChanged, timeout)
