# Copyright 2014 WUSTL ZPLAB
# Erik Hvatum (ice.rikh@gmail.com)

from acquisition.device import Device

class Camera_mm(Device):
    def __init__(self, mmcore):
        super().__init__('Andor Zyla')
        self._appendTypeName('Camera_mm')
        self._mmcore = mmcore
        self._mmDeviceName = self._mmcore.getCameraDevice()

        self.snapImage = self._mmcore.snapImage
        self.getImage = self._mmcore.getImage

    @property
    def exposure(self):
        return self._mmcore.getExposure()

    @exposure.setter
    def exposure(self, exposure):
        self._mmcore.setExposure(exposure)

    @property
    def roi(self):
        '''Returns [xmin, ymin, width, height].'''
        return self._mmcore.getROI()

    @roi.setter
    def roi(self, roi):
        '''For the roi argument, supply a tuple, list, etc in the form [xmin, ymin, width, height].'''
        self._mmcore.setROI(roi[0], roi[1], roi[2], roi[3])

    @property
    def shutter(self):
        return self._mmcore.getProperty(self._mmDeviceName, 'ElectronicShutteringMode')

    @shutter.setter
    def shutter(self, shutter):
        self._mmcore.setProperty(self._mmDeviceName, 'ElectronicShutteringMode', shutter)

