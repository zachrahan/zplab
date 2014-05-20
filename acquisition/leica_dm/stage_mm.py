# Copyright 2014 WUSTL ZPLAB
# Erik Hvatum (ice.rikh@gmail.com)

from acquisition.device import Device

class Stage_mm(Device):
    _mmXyName = 'XYStage'
    _mmZName = 'FocusDrive'

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
        return self._mmcore.getXPosition(Stage_mm._mmXyName)

    @posX.setter
    def posX(self, x):
        self._mmcore.setXPosition(Stage_mm._mmXyName, x)

    @property
    def posY(self):
        return self._mmcore.getYPosition(Stage_mm._mmXyName)

    @posY.setter
    def posY(self, y):
        self._mmcore.setYPosition(Stage_mm._mmXyName, y)

    @property
    def posZ(self):
        return self._mmcore.getPosition(Stage_mm._mmZName)

    @posZ.setter
    def posZ(self, z):
        self._mmcore.setPosition(Stage_mm._mmZName, z)
