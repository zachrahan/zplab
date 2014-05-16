# Copyright 2014 WUSTL ZPLAB
# Erik Hvatum (ice.rikh@gmail.com)

from acquisition.device import Device

class Stage_mm(Device):
    def __init__(self, mmcore):
        super().__init__('Leica Stage')
        self._appendTypeName('Stage_mm')
        self._mmcore = mmcore

    @property
    def pos(self):
        '''Stage coordinates in a tuple ordered (x, y, z).'''
        return (self.posX, self.posY, self.posZ)

    @pos.setter
    def pos(self, coords):
        self.posX = coords[0]
        self.posY = coords[1]
        self.posZ = coords[2]

    @property
    def posX(self):
        return self._mmcore.getXPosition('XYStage')

    @posX.setter
    def posX(self, x):
        self._mmcore.setXPosition('XYStage', x)

    @property
    def posY(self):
        return self._mmcore.getYPosition('XYStage')

    @posY.setter
    def posY(self, y):
        self._mmcore.setYPosition('XYStage', y)

    @property
    def posZ(self):
        return self._mmcore.getPosition('FocusDrive')

    @posZ.setter
    def posZ(self, z):
        self._mmcore.setPosition('FocusDrive', z)
