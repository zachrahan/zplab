# Copyright 2014 WUSTL ZPLAB
# Erik Hvatum (ice.rikh@gmail.com)

import os
from PyQt5 import Qt, uic
from acquisition.andor.andor import Camera
from acquisition.device import DeviceException

class CameraManipDialog(Qt.QDialog):
    def __init__(self, parent, cameraInstance):
        super().__init__(parent)
        self.cameraInstance = cameraInstance

        # Note that uic.loadUiType(..) returns a tuple containing two class types (the form class and the Qt base
        # class).  The line below instantiates the form class.  It is assumed that the .ui file resides in the same
        # directory as this .py file.
        self.ui = uic.loadUiType(os.path.join(os.path.dirname(__file__), 'direct_manip.ui'))[0]()
        self.ui.setupUi(self)

        self.ui.cameraModelEdit.setText(self.cameraInstance.cameraModel)
        self.ui.serialNumberEdit.setText(self.cameraInstance.serialNumber)
        self.ui.interfaceTypeEdit.setText(self.cameraInstance.interfaceType)
        self.ui.sensorWidthEdit.setText(str(self.cameraInstance.sensorWidth))
        self.ui.sensorHeightEdit.setText(str(self.cameraInstance.sensorHeight))

        def addSpinBoxProp(propName):
            evalStr = 'self.ui.{0}SpinBox.setValue(self.cameraInstance.{0})\n'
            evalStr+= 'self.ui.{0}SpinBox.valueChanged.connect(lambda value, self=self, propName=propName: self.cameraInstance.setProperty(propName, value))\n'
            evalStr+= 'self.cameraInstance.{0}Changed.connect(lambda value, self=self: self.ui.{0}SpinBox.setValue(value))'
            exec(evalStr.format(propName), {'self':self, 'propName':propName})

        def addRoEditProp(propName):
            evalStr = 'self.ui.{0}Edit.setText(str(self.cameraInstance.{0}))\n'
            evalStr+= 'self.cameraInstance.{0}Changed.connect(lambda value, self=self: self.ui.{0}Edit.setText(str(value)))'
            exec(evalStr.format(propName), {'self':self, 'propName':propName})

        def addComboProp(propName):
            enumName = propName[0].upper() + propName[1:]
            es = eval('[(name, int(value)) for name, value in self.cameraInstance.{}.names.items()]'.format(enumName), {'self':self})
            es.sort(key=lambda both: both[1])
            evalStr = ''
            for e in es:
                evalStr += 'self.ui.{}Combo.addItem("{}")\n'.format(propName, e[0])
            evalStr+= 'self.ui.{0}Combo.setCurrentIndex(int(self.cameraInstance.{0}))\n'
            evalStr+= 'print("self.ui.{0}Combo.currentIndexChanged[int].connect(lambda value, self=self, propName=propName: '
            evalStr+= 'self.cameraInstance.setProperty(propName, self.cameraInstance.{1}(value)))")\n'
#           evalStr+= 'self.cameraInstance.{0}Changed.connect(lambda value, self=self: self.ui.{0}Combo.setCurrentIndex(int(value)))'
#           evalStr+= 'self.cameraInstance.{0}Changed.connect(lambda value, self=self: print("{0}:", value))'
            exec(evalStr.format(propName, enumName), {'self':self, 'propName':propName})

        addSpinBoxProp('accumulateCount')
        addSpinBoxProp('aoiLeft')
        addSpinBoxProp('aoiTop')
        addSpinBoxProp('aoiWidth')
        addSpinBoxProp('aoiHeight')
        addRoEditProp('aoiStride')
        addComboProp('auxiliaryOutSource')

def show(cameraInstance=None, launcherDescription=None, moduleArgs=None):
    import sys
    import argparse

    parser = argparse.ArgumentParser(launcherDescription)
    parser.add_argument('--andor-device-index', type=int, help="The index of the Andor camera you wish to manipulate.  For example, if " +
        "acquisition.andor.andor.Camera.getDeviceNames() returns ['ZYLA-5.5-CL3', 'SIMCAM CMOS', 'SIMCAM CMOS'], then --andor-device-index=0 " +
        "would select ZYLA-5.5-CL3, whereas --andor-device-index=1 would select the first SIMCAM CMOS.", dest='andorDeviceIndex')
    args = parser.parse_args(moduleArgs)

    app = Qt.QApplication(sys.argv)
    if cameraInstance is None:
        if args.andorDeviceIndex is None:
            cameraInstance = Camera()
        else:
            cameraInstance = Camera(andorDeviceIndex=args.andorDeviceIndex)
    dialog = CameraManipDialog(None, cameraInstance)
    sys.exit(dialog.exec_())
