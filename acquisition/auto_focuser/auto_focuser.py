# The MIT License (MIT)
#
# Copyright (c) 2014-2015 WUSTL ZPLAB
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
import sys
import time
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
        self._zDrive.posChanged.connect(self._zDrivePosChanged)
        self._steps = None
        self._stepIdx = None
        self._results = None
        self._round = None
        self.rw = None
        self.brennerTotal = 0
        self.acqTotal = 0

    def _brenner(self, im, direction):
        t0 = time.time()
        if direction == 'h':
            xo = 2
            yo = 0
        elif direction == 'v':
            xo = 0
            yo = 2
        else:
            raise ValueError('direction must be h or v.')
        iml = numpy.pad(im[0:im.shape[0]-yo, 0:im.shape[1]-xo], ((yo, 0), (xo, 0)), mode='constant')
        imr = im.copy()
        if direction == 'h':
            imr[:, :xo] = 0
        else:
            imr[:yo, :] = 0
        self.brennerTotal += time.time() - t0
        return iml - imr

    def _brennervh(self, im):
        imh = self._brenner(im, 'h')
        imv = self._brenner(im, 'v')
        return numpy.sqrt(imh**2 + imv**2)

    def _ss(self, im):
        im = im.astype(numpy.float64)
#       if self._useMask:
#           im = numpy.ma.array(im, mask=self._mask)
        return (im**2).sum()

    def _zDrivePosChanged(self, foo):
        # If we are currently auto-focusing and the z drive has stopped moving...
        if self._busy and not self._zDrive.moving:
            zDrivePos = self._zDrive.pos
            reqzDrivePos = self._steps[self._stepIdx]
            if abs(zDrivePos - reqzDrivePos) > self._zDrive._factor - sys.float_info.epsilon:
                w = 'Current Z position ({0}) does not match requested Z position ({1}).  '
                w+= 'The autofocus step for {1} is being skipped.  This can occur if the requested Z position '
                w+= 'is out of range or if the scope\'s Z position controller has been moved during the '
                w+= 'auto-focus operation.'
                self._warn(w.format(zDrivePos, reqzDrivePos))
            else:
                t0 = time.time()
                im = self._camera.acquireImage()
                self.acqTotal += time.time() - t0
                if self.rw is not None:
                    self.rw.showImage(im)
                im = (im.astype(numpy.float32) / 65535)
                im = self._brennervh(im)
                result = self._ss(im)
                print(result, zDrivePos)
                self._results.append((zDrivePos, result))
            self._stepIdx += 1
            if self._stepIdx == len(self._steps):
                noResults = len(self._results) == 0
                if not noResults:
                    if self._round in (1,2):
                        self._round += 1
                        self._stepIdx = 0
                        bestZidx = numpy.array([r[1] for r in self._results], dtype=numpy.float64).argmax()
                        belowZidx = max(bestZidx - 1, 0)
                        aboveZidx = min(bestZidx + 1, len(self._results) - 1)
                        self._steps = numpy.linspace(self._steps[belowZidx], self._steps[aboveZidx], len(self._steps))
                        self._results = []
                        self._zDrive.pos = self._steps[0]
                    else:
                        self._stepIdx = None
                        self._busy = False
                        self.busyChanged.emit(self._busy)
                        if noResults:
                            raise DeviceException(self, 'Failed to move to any of the specified Z positions.')
                        # Sort position/focus measure result pairs by focus measure result in descending order
                        self._results.sort(key=lambda v:v[1], reverse=True)
                        # Move to the best position
                        self._zDrive.pos = self._results[0][0]
                        if self.rw is not None:
                            self._zDrive.waitForReady()
                            im = self._camera.acquireImage()
                            self.rw.showImage(im)
                if noResults:
                    self._stepIdx = None
                    self._busy = False
                    self.busyChanged.emit(self._busy)
                    raise DeviceException(self, 'Failed to move to any of the specified Z positions.')
            else:
                self._zDrive.pos = self._steps[self._stepIdx]

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
        self._stepIdx = 0
        self._steps = numpy.linspace(minZ, maxZ, initialStepCount)
        self._results = []
        self._busy = True
        self._round = 1
        self._zDrive.pos = self._steps[0]
        self.busyChanged.emit(self._busy)

    def stopAutoFocus(self):
        if not self._busy:
            # If an auto focus operation is not in progress, requests to stop auto focusing are ignored
            return

    def waitForReady(self, timeout=None):
        if self._busy:
            self._waitForSignal(self.busyChanged, timeout)
