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
        self.ui.pixelWidthEdit.setText(str(self.cameraInstance.pixelWidth))
        self.ui.pixelHeightEdit.setText(str(self.cameraInstance.pixelHeight))

        def addSpinBoxProp(propName):
            evalStr = 'self.ui.{0}SpinBox.setValue(self.cameraInstance.{0})\n'
            evalStr+= 'self.ui.{0}SpinBox.valueChanged.connect(lambda value, cameraInstance=self.cameraInstance, propName=propName: cameraInstance.setProperty(propName, value))\n'
            evalStr+= 'self.cameraInstance.{0}Changed.connect(lambda value, spinBox=self.ui.{0}SpinBox: spinBox.setValue(value))'
            exec(evalStr.format(propName), {'self':self, 'propName':propName})

        def addRoEditProp(propName):
            evalStr = 'self.ui.{0}Edit.setText(str(self.cameraInstance.{0}))\n'
            evalStr+= 'self.cameraInstance.{0}Changed.connect(lambda value, edit=self.ui.{0}Edit: edit.setText(str(value)))'
            exec(evalStr.format(propName), {'self':self, 'propName':propName})

        def addComboProp(propName):
            if propName == 'ioSelector':
                enumName = 'IOSelector'
            else:
                enumName = propName[0].upper() + propName[1:]
            es = eval('[(name, int(value)) for name, value in self.cameraInstance.{}.names.items()]'.format(enumName), {'self':self})
            es.sort(key=lambda both: both[1])
            evalStr = ''
            for e in es:
                evalStr += 'self.ui.{}Combo.addItem("{}")\n'.format(propName, e[0])
            evalStr+= 'self.ui.{0}Combo.setCurrentIndex(int(cameraInstance.{0}))\n'
            evalStr+= 'def onChange(value):\n'
            evalStr+= '    cameraInstance.{0} = cameraInstance._camera.{1}(value)\n'
            evalStr+= 'self.ui.{0}Combo.currentIndexChanged[int].connect(onChange)\n'
            evalStr+= 'cameraInstance.{0}Changed.connect(lambda value, combo=self.ui.{0}Combo: combo.setCurrentIndex(int(value)))\n'
            exec(evalStr.format(propName, enumName), {'self':self, 'propName':propName, 'cameraInstance':self.cameraInstance})

        def addRoEnumProp(propName):
            enumName = propName[0].upper() + propName[1:]
            es = eval('[(name, int(value)) for name, value in self.cameraInstance.{}.names.items()]'.format(enumName), {'self':self})
            es.sort(key=lambda both: both[1])
            names = [e[0] for e in es]
            del enumName, es
            evalStr = 'self.ui.{0}Edit.setText(names[int(cameraInstance.{0})])\n'
            evalStr+= 'cameraInstance.{0}Changed.connect(lambda value, edit=self.ui.{0}Edit, names=names: edit.setText(names[int(value)]))'
            exec(evalStr.format(propName), {'self':self, 'names':names, 'cameraInstance':self.cameraInstance})

        def addCheckBoxProp(propName):
            evalStr = 'self.ui.{0}CheckBox.setCheckState(Qt.Qt.Checked if self.cameraInstance.{0} else Qt.Qt.Unchecked)\n'
            evalStr+= 'self.ui.{0}CheckBox.toggled.connect(lambda value, cameraInstance=self.cameraInstance, propName=propName: cameraInstance.setProperty(propName, value))\n'
            evalStr+= 'self.cameraInstance.{0}Changed.connect(lambda value, checkBox=self.ui.{0}CheckBox, Qt=Qt: checkBox.setCheckState(Qt.Qt.Checked if value else Qt.Qt.Unchecked))'
            exec(evalStr.format(propName), {'self':self, 'propName':propName, 'Qt':Qt})

        def addRoCheckBoxProp(propName):
            evalStr = 'self.ui.{0}CheckBox.setCheckState(Qt.Qt.Checked if self.cameraInstance.{0} else Qt.Qt.Unchecked)\n'
            evalStr+= 'self.cameraInstance.{0}Changed.connect(lambda value, checkBox=self.ui.{0}CheckBox, Qt=Qt: checkBox.setCheckState(Qt.Qt.Checked if value else Qt.Qt.Unchecked))'
            exec(evalStr.format(propName), {'self':self, 'propName':propName, 'Qt':Qt})

        addSpinBoxProp('accumulateCount')
        addSpinBoxProp('aoiLeft')
        addSpinBoxProp('aoiTop')
        addSpinBoxProp('aoiWidth')
        addSpinBoxProp('aoiHeight')
        addRoEditProp('aoiStride')
        addComboProp('auxiliaryOutSource')
        addComboProp('binning')
        addRoEditProp('bytesPerPixel')
        addComboProp('cycleMode')
        addSpinBoxProp('exposureTime')
        addComboProp('fanSpeed')
        addSpinBoxProp('frameCount')
        addSpinBoxProp('frameRate')
        addRoEditProp('imageSizeBytes')
        addComboProp('ioSelector')
        addCheckBoxProp('ioInvert')
        addRoEditProp('maxInterfaceTransferRate')
        addCheckBoxProp('metadataEnabled')
        addCheckBoxProp('metadataTimestampEnabled')
        addCheckBoxProp('overlap')
        addRoEnumProp('pixelEncoding')
        addComboProp('pixelReadoutRate')
        addRoEditProp('readoutTime')
        addCheckBoxProp('sensorCooling')
        addRoCheckBoxProp('acquisitionSequenceInProgress')
        addComboProp('shutter')
        addComboProp('simplePreAmp')
        addCheckBoxProp('spuriousNoiseFilter')
        addSpinBoxProp('timestampClockFrequency')
        addComboProp('triggerMode')

        # The cameraInstance.waitBufferTimeout property, being the only property composed of an enum AND a float, is complex and a one-off
        # special case.  So, unlike the properties managed above, it's not generalized into an addxxxxxx function.
        for e in Camera.WaitBufferTimeout:
            self.ui.waitBufferTimeoutCombo.addItem(e.name)
        self._waitBufferTimeoutChangedSlot(self.cameraInstance.waitBufferTimeout)
        self.cameraInstance.waitBufferTimeoutChanged.connect(self._waitBufferTimeoutChangedSlot)
        self.ui.waitBufferTimeoutCombo.currentIndexChanged.connect(self._waitBufferComboIndexChangedSlot)
        self.ui.waitBufferTimeoutSpinBox.valueChanged.connect(self._waitBufferSpinBoxValueChangedSlot)

        self.ui.resetTimestampClockButton.clicked.connect(self.cameraInstance.commandTimestampClockReset)
        self.ui.softwareTriggerButton.clicked.connect(self.cameraInstance.commandSoftwareTrigger)
        self.ui.startAcquisitionSequenceButton.clicked.connect(self.cameraInstance.startAcquisitionSequence)
        self.ui.stopAcquisitionSequenceButton.clicked.connect(self.cameraInstance.stopAcquisitionSequence)

        self.cameraInstance.inLiveModeChanged.connect(self._inLiveModeChangedSlot)
        self.ui.enterExitLiveModeButton.clicked.connect(self._enterExitLiveModeButtonClickedSlot)

    def closeEvent(self, event):
        super().closeEvent(event)
        self.deleteLater()

    def _waitBufferTimeoutChangedSlot(self, waitBufferTimeout):
        self.ui.waitBufferTimeoutCombo.setCurrentIndex(waitBufferTimeout[0].value)
        if waitBufferTimeout[0] is Camera.WaitBufferTimeout.Override:
            self.ui.waitBufferTimeoutSpinBox.setVisible(True)
            self.ui.waitBufferTimeoutSpinBox.setValue(waitBufferTimeout[1])
        else:
            self.ui.waitBufferTimeoutSpinBox.setVisible(False)

    # Note: decorator required to disambiguate by argument type between overloaded combo box index change signals
    @Qt.pyqtSlot(int)
    def _waitBufferComboIndexChangedSlot(self, index):
        e = Camera.WaitBufferTimeout(index)
        if e is Camera.WaitBufferTimeout.Override:
            self.cameraInstance.waitBufferTimeout = (e, self.ui.waitBufferTimeoutSpinBox.value())
        else:
            self.cameraInstance.waitBufferTimeout = (e,)

    def _waitBufferSpinBoxValueChangedSlot(self, value):
        if self.cameraInstance.waitBufferTimeout[0] is Camera.WaitBufferTimeout.Override:
            self.cameraInstance.waitBufferTimeout = (Camera.WaitBufferTimeout.Override, value)

    def _inLiveModeChangedSlot(self, value):
        if value:
            self.ui.enterExitLiveModeButton.setText('Exit Live Mode')
        else:
            self.ui.enterExitLiveModeButton.setText('Enter Live Mode')

    def _enterExitLiveModeButtonClickedSlot(self):
        self.cameraInstance.inLiveMode = not self.cameraInstance.inLiveMode

def show(cameraInstance=None, launcherDescription=None, moduleArgs=None):
    import argparse
    import sys
    import gc

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
    ret = dialog.exec_()
    del dialog
    del cameraInstance
    gc.collect()
    sys.exit(ret)
