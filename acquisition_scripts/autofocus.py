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

import numpy
from PyQt5 import Qt
import skimage.filter
import skimage.morphology
import sys
import time



def _brenner(im, direction):
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
    return iml - imr

def brennerFocusMeasure(im):
    im = im.astype(numpy.float32) / 65535
    imh = _brenner(im, 'h')
    imv = _brenner(im, 'v')
    return numpy.sqrt(imh**2 + imv**2)

def cannyFocusMeasure(im):
    try:
        return skimage.filter.canny(im).astype(numpy.float32)
    except ValueError as e:
        return None

def bottomhatFocusMeasure(im, structureElement=None):
    if structureElement is None:
        structureElement = skimage.morphology.disk(5)
    try:
        return skimage.filter.rank.bottomhat((im / 256).astype(numpy.uint8), structureElement).astype(numpy.float32) / 255
    except ValueError as e:
        return None

def bottomhatGaussianFocusMeasure(im, structureElement=None, sigma=0.5):
    if structureElement is None:
        structureElement = skimage.morphology.disk(5)
    try:
        return skimage.filter.rank.bottomhat((skimage.filter.gaussian_filter(im.astype(numpy.float32) / 65535, sigma) * 255).astype(numpy.uint8), structureElement).astype(numpy.float32) / 255
    except ValueError as e:
        print('errored')
        return None

def tophatFocusMeasure(im, structureElement=None):
    if structureElement is None:
        structureElement = skimage.morphology.disk(5)
    try:
        return skimage.filter.rank.tophat((im / 256).astype(numpy.uint8), structureElement).astype(numpy.float32) / 255
    except ValueError as e:
        return None

def tophatGaussianFocusMeasure(im, structureElement=None, sigma=0.5):
    if structureElement is None:
        structureElement = skimage.morphology.disk(5)
    try:
        return skimage.filter.rank.tophat((skimage.filter.gaussian_filter(im.astype(numpy.float32) / 65535, sigma) * 255).astype(numpy.uint8), structureElement).astype(numpy.float32) / 255
    except ValueError as e:
        return None

def coroutine(func):
    def start(*args,**kwargs):
        cr = func(*args,**kwargs)
        next(cr)
        return cr
    return start

class LinearSearchAutofocuser(Qt.QObject):
    # Autofocus completed successfully if signal parameter is True
    autoFocusDone = Qt.pyqtSignal(bool)
    # Used internally to emit done signal after generator has exited, preventing call stack from getting totally out of control
    _relayAutoFocusDone = Qt.pyqtSignal(bool)

    def __init__(self, camera, zDrive, minZ, maxZ, stepsPerRound, numberOfRounds, focusMeasure=brennerFocusMeasure, rw=None):
        super().__init__()
        self._camera = camera
        self._zDrive = zDrive
        self._zRange = (minZ, maxZ)
        self._stepsPerRound = stepsPerRound
        self._numberOfRounds = numberOfRounds
        self._focusMeasure = focusMeasure
        self._rw = rw
        self.bestZ = None
        self._runGen = None
        self._relayAutoFocusDone.connect(self._relayAutoFocusDoneSlot, Qt.Qt.QueuedConnection)

    def abort(self):
        if self._runGen is not None:
            try:
                self._runGen.send(False)
            except StopIteration:
                pass

    def start(self):
        if self._runGen is not None:
            raise RuntimeError('LinearSearchAutofocuser is already running.')
        self._runGen = self._run()

    def _relayAutoFocusDoneSlot(self, succeeded):
        self._zDrive.posChanged.disconnect(self._zDrivePosChanged)
        self._runGen = None
        self.autoFocusDone.emit(succeeded)

    @coroutine
    def _run(self):
        t0 = time.time()
        self.bestZ = None
        self._zDrive.posChanged.connect(self._zDrivePosChanged)
        self._running = True

        curZRange = self._zRange
        buffers = [self._camera.makeAcquisitionBuffer() for i in range(self._stepsPerRound)]
        
        for roundIdx in range(0, self._numberOfRounds):
            print('Starting autofocus round {}.'.format(roundIdx))
            fmvs = []
            stepIdxsDone = []
            if roundIdx == 0:
                # The first round computes focus measures for every step in the Z range, including endpoints
                steps = numpy.linspace(*curZRange, num=self._stepsPerRound)
            else:
                # Every subsequent round's Z range is the interval between the previous round's Z steps bracketing the Z step
                # with the highest focus measure value:
                #
                # ----- Previous Z step above best previous Z
                #   | --- Current Z step
                #   | --- "
                #   | --- "
                # ----- Previous Z step with best focus measure value
                #   | --- Current Z step
                #   | --- "
                #   | --- "
                # ----- Previous Z step below best previous Z
                #
                # So, if a subsequent round's step sequence is computed in the same manner as the first round's step sequence,
                # it will include the previous round's bracketing Z step positions as endpoints, repeating the focus measure
                # computation for those positions, increasing the computational expense of the linear search.  This is most clearly
                # illustrated by the case where stepsPerRound is 3 and first round best Z step is the middle position: in this case,
                # the linear search will repeat the same calculations at the same Z step positions for an arbitrary number of rounds,
                # failing to refine the best Z step position.
                #
                # This is avoided while maintaining uniform step size by treating subsequent Z ranges as an open interval bounded
                # by bracketing Z step positions.  If stepsPerRound is odd, the best previous Z step position focus measure is
                # still recomputed, but this is considered acceptable.
                steps = numpy.linspace(*curZRange, num=self._stepsPerRound+2)[1:-1]
            self._camera._camera.AT_Flush()
            self._camera.shutter = self._camera.Shutter.Rolling
            self._camera.triggerMode = self._camera.TriggerMode.Software
            self._camera.cycleMode = self._camera.CycleMode.Fixed
            self._camera.frameCount = self._stepsPerRound

            for buffer in buffers:
                self._camera._camera.AT_QueueBuffer(buffer)
            self._camera._camera.AT_Command(self._camera._camera.Feature.AcquisitionStart)

            for stepIdx, z in enumerate(steps):
                self._zDrive.pos = z
                # Return to main event loop (or whatever was the enclosing greenlet when this class was instantiated) until
                # the stage stops moving, aborting and cleaning up if resumed with switch(False)
                keepGoing = yield
                if not keepGoing:
                    print('Autofocus aborted.')
                    self._camera._camera.AT_Command(self._camera._camera.Feature.AcquisitionStop)
                    self._camera._camera.AT_Flush()
                    self._relayAutoFocusDone.emit(False)
                    return
                # Resuming after stage has moved
                actualZ = self._zDrive.pos
                if abs(actualZ - z) > self._zDrive._factor - sys.float_info.epsilon:
                    w = 'Current Z position ({0}) does not match requested Z position ({1}).  '
                    w+= 'The autofocus step for {1} is being skipped.  This can occur if the requested Z position '
                    w+= 'is out of range or if the scope\'s Z position controller has been moved during the '
                    w+= 'auto-focus operation.'
                    print(w.format(actualZ, z))
                    continue
                # Stage Z position is actually what we requested.  Command exposure.
                self._camera.commandSoftwareTrigger()
                print('exposed ', stepIdx)
                stepIdxsDone.append(stepIdx)

            # Retrieve, show, and process resulting exposures
            for bufferIdx, stepIdx in enumerate(stepIdxsDone):
                self._camera._camera.AT_WaitBuffer(1000)
                print('got buffer', bufferIdx)
                buffer = buffers[bufferIdx]
                if self._rw is not None:
                    self._rw.showImage(buffer)
                fmv = (self._focusMeasure(buffer)**2).sum()
                print('round={:02}, z={:<10}, focus_measure={}'.format(roundIdx, steps[stepIdx], fmv))
                fmvs.append((steps[stepIdx], fmv))

            self._camera._camera.AT_Command(self._camera._camera.Feature.AcquisitionStop)

            if len(fmvs) == 0:
                print('Failed to move to any of the Z step positions.')
                self._relayAutoFocusDone.emit(False)
                return
            if len(fmvs) == 1:
                print('Successfully moved to only one of the Z step positions, making that position the best found.')
                self.bestZ = fmvs[0][0]
                self._relayAutoFocusDone.emit(True)
                return

            bestZIdx = numpy.array([fmv[1] for fmv in fmvs], dtype=numpy.float64).argmax()

            if roundIdx + 1 < self._numberOfRounds:
                # Next round, search the range between the steps adjacent to the best step
                curZRange = ( steps[max(bestZIdx - 1, 0)],
                              steps[min(bestZIdx + 1, len(fmvs) - 1)] )
            else:
                # There is no next round.  Store result.
                self.bestZ = steps[bestZIdx]

        print('Autofocus completed ({}s).'.format(time.time() - t0))
        self._relayAutoFocusDone.emit(True)

    def _zDrivePosChanged(self, _):
        if self._runGen is not None and not self._zDrive.moving:
            try:
                self._runGen.send(True)
            except StopIteration:
                pass
