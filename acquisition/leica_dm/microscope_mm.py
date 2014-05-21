# Copyright 2014 WUSTL ZPLAB
# Erik Hvatum (ice.rikh@gmail.com)

from acquisition.andor.andor import Camera
from acquisition.brightfield_led.brightfield_led import BrightfieldLed
from acquisition.device import Device
from acquisition.leica_dm.stage_mm import Stage_mm
from acquisition.lumencor.lumencor import Lumencor
import sys

mmpath = '/mnt/scopearray/mm/micro-manager/MMCorePy_wrap/build/lib.linux-x86_64-3.3'
if mmpath not in sys.path:
    sys.path.insert(0, mmpath)
del mmpath

import MMCorePy

class Microscope_mm(Device):
    def __init__(self, mmcore=None):
        super().__init__('Leica DM6000')
        self._appendTypeName('Microscope_mm')

        if mmcore is None:
            self._mmcore = MMCorePy.CMMCore()
            self._mmcore.loadSystemConfiguration("/mnt/scopearray/mm/ImageJ/scope_only.cfg")
        else:
            self._mmcore = mmcore

        self._brightfieldLed = BrightfieldLed()
        self._addSubDevice(self._brightfieldLed)
        self._camera = Camera(0)
        self._addSubDevice(self._camera)
        self._stage = Stage_mm(self._mmcore)
        self._addSubDevice(self._stage)

    # Properties for accessing subdevices are in approximate ascending order of position along the microscope's vertical
    # axis.  The condensor is below the stage, which lies beneath the objectives, etc.  The Peltier controller box happened
    # to be below everything else when this was written.

    @property
    def peltier(self):
        return None

    @property
    def brightfieldLed(self):
        return self._brightfieldLed

    @property
    def stage(self):
        return self._stage

    @property
    def lumencor(self):
        return self._lumencor

    @property
    def camera(self):
        return self._camera
