# Copyright 2014 WUSTL ZPLAB

import sys

mmpath = '/mnt/scopearray/mm/micro-manager/MMCorePy_wrap/build/lib.linux-x86_64-3.3'
if mmpath not in sys.path:
    sys.path.insert(0, mmpath)
del mmpath

import MMCorePy



class Microscope:
    def __init__(self, mmcore=None):
        if mmcore is None:
            self.mmcore = MMCorePy.CMMCore()
        else:
            self.mmcore = mmcore
        self.getExposure = self.mmcore.getExposure
        self.setExposure = self.mmcore.setExposure
        self.snapImage = self.mmcore.snapImage
        self.getImage = self.mmcore.getImage

    @property
    def stagePos(self):
        '''Stage coordinates in a tuple ordered (x, y, z).'''
        return (self.stagePosX, self.stagePosY, self.stagePosZ)

    @stagePos.setter
    def stagePos(self, coords):
        self.stagePosX = coords[0]
        self.stagePosY = coords[1]
        self.stagePosZ = coords[2]

    @property
    def stagePosX(self):
        return self.mmcore.getXPosition('XYStage')

    @stagePosX.setter
    def stagePosX(self, x):
        self.mmcore.setXPosition('XYStage', x)

    @property
    def stagePosY(self):
        return self.mmcore.getYPosition('XYStage')

    @stagePosY.setter
    def stagePosY(self, y):
        self.mmcore.setYPosition('XYStage', y)

    @property
    def stagePosZ(self):
        return self.mmcore.getPosition('FocusDrive')

    @stagePosZ.setter
    def stagePosZ(self, z):
        self.mmcore.setPosition('FocusDrive', z)
