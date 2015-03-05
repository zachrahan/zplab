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

from skimage import io as skio
for function in ('imread', 'imsave', 'imread_collection'):
    skio.use_plugin('freeimage', function)
from pathlib import Path
from acquisition.andor.andor import Camera
import acquisition.auto_focuser.auto_focuser
from acquisition.auto_focuser.auto_focuser import AutoFocuser
from acquisition.brightfield_led.brightfield_led import BrightfieldLed
from acquisition.device import Device, DeviceException
from acquisition.dm6000b.dm6000b import Dm6000b
from acquisition.lumencor.lumencor import Lumencor
from acquisition.pedals.pedals import Pedals
#from acquisition.peltier.peltier import Peltier
from acquisition.peltier.incubator import Incubator

class Root(Device):
    '''The Device representing the root of the device hierarchy.  At the moment, it is convenient for the
    root device to represent zplab-scope, which is the computer running the show.  All device are currently
    directly or indirectly attached to zplab-scope.  It may make sense to abstract the root device into
    a virtual device that has individual computers as its subdevices at some point in the future.'''
    def __init__(self):
        super().__init__(deviceName='zplab-scope Linux system')

#       self._peltier = Peltier(self)
        self._incubator = Incubator('/dev/ttyPeltier')
        self._brightfieldLed = BrightfieldLed(self, serialPortDescriptor='/dev/ttyACM0')
        self._dm6000b = Dm6000b(self)
        self._lumencor = Lumencor(self)
        self._camera = Camera(self, andorDeviceIndex=0)
        self._autoFocuser = AutoFocuser(parent=self, camera=self._camera, zDrive=self._dm6000b.stageZ)
        self._pedals = Pedals()

        # This is a logical place to set up auto focus parameters as auto focus is not tightly coupled
        # with other implementation details.  If some sort of config file functionality is added, then
        # the following code should be abstracted to use mask & objective position data read from the
        # config file.
        autoFocuserSrcDir = Path(acquisition.auto_focuser.auto_focuser.__file__).parent
        mask5x = skio.imread(str(autoFocuserSrcDir / '5x_mask.png'))
        mask10x = skio.imread(str(autoFocuserSrcDir / '10x_mask.png'))
        self._objectivePositionAutoFocusMasks = {1 : mask5x, 2 : mask10x}
        self._dm6000b.objectiveTurret.posChanged.connect(self._objectiveChanged)
        # Trickiness: although objectiveTurret position queries may have been issued by this time,
        # the handler that reads the responses and sets the objectiveTurret.pos property has not -
        # that handler runs on this thread, so we have been blocking it since calling its constructor
        # (via Dm6000b's constructor) above.  Therefore, our auto-focus-mask-setting _objectiveChanged
        # slot/handler will not be called until after returning from this function, relieving us of the
        # need to call self._objectiveChanged() once here.

    def _objectiveChanged(self):
        pos = self._dm6000b.objectiveTurret.pos
        if pos == 0 and pos is not None:
            # Interim pos value of 0 indicating that objective turret is in the process of switching positions or
            # indicating that objective turret has been manually placed between positions is ignored.  Likewise,
            # None, indicating that pos value has not yet been read from the stand is ignored. Mask is only updated
            # when a real (possibly empty) objective position is reached.
            return
        if pos in self._objectivePositionAutoFocusMasks:
            self._autoFocuser.useMask = True
            self._autoFocuser.mask = self._objectivePositionAutoFocusMasks[pos]
        else:
            self._autoFocuser.useMask = False

    # Properties for accessing devices are in approximate ascending order of vertical position.  The Peltier
    # controller box happened to be below everything else when this was written.

#   @property
#   def peltier(self):
#       return self._peltier

    @property
    def pedals(self):
        return self._pedals

    @property
    def incubator(self):
        return self._incubator

    @property
    def brightfieldLed(self):
        return self._brightfieldLed

    @property
    def dm6000b(self):
        return self._dm6000b

    @property
    def lumencor(self):
        return self._lumencor

    @property
    def camera(self):
        return self._camera

    @property
    def autoFocuser(self):
        return self._autoFocuser

    def waitForReady(self):
        self._autoFocuser.waitForReady()
        self._dm6000b.waitForReady()
