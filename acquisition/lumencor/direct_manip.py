# Copyright 2014 WUSTL ZPLAB

import os
from PyQt5 import QtCore, QtGui, QtWidgets, uic
from acquisition.lumencor.lumencor import Lumencor
from acquisition.lumencor.lumencor_exception import LumencorException

class LumencorManipDialog(QtWidgets.QDialog):
    class ColorControlSet:
        def __init__(self, toggle, slider, spinBox, setEnabled, setPower):
            self.toggle = toggle
            self.slider = slider
            self.spinBox = spinBox
            self.setEnabled = setEnabled
            self.setPower = setPower

    def __init__(self, parent, lumencorInstance):
        super(LumencorManipDialog, self).__init__(parent)
        self.lumencorInstance = lumencorInstance

        # Note that uic.loadUiType(..) returns a tuple containing two class types (the form class and the Qt base
        # class).  The line below instantiates the form class.  It is assumed that the .ui file resides in the same
        # directory as this .py file.
        self.ui = uic.loadUiType(os.path.join(os.path.dirname(__file__), 'direct_manip.ui'))[0]()
        self.ui.setupUi(self)

        evalstr  = 'self.ColorControlSet(self.ui.{0}Toggle, self.ui.{0}Slider, self.ui.{0}SpinBox, '
        evalstr += 'Lumencor.__dict__["{0}Enabled"].__set__, Lumencor.__dict__["{0}Power"].__set__)'

        self.colorControlSets = {color : eval(evalstr.format(color), {'self':self, 'Lumencor':Lumencor}) for color in Lumencor._lampNames}

        # Update interface to reflect current state of Lumencor box (which may be something other than default if this dialog was
        # attached to an existing Lumencor instance that has previously been manipulated)
        self.deviceLampStatesChangedSlot({ln : {'enabled' : ls.enabled, 'power' : ls.power} for ln, ls in self.lumencorInstance.lampStates.items()})

        for c, ccs in self.colorControlSets.items():
            # Handle toggle by color name so color enable/disable command can be sent to lumencor driver
            ccs.toggle.toggled.connect(lambda on, colorControlSet=ccs: self.colorEnabledWidgetToggledSlot(colorControlSet, on))
            # Send slider changes to lumencor driver
            ccs.slider.sliderMoved.connect(lambda intensity, colorControlSet=ccs: self.colorIntensityWidgetChangedSlot(colorControlSet, intensity))
            # Send spinbox changes to lumencor driver
            ccs.spinBox.valueChanged.connect(lambda intensity, colorControlSet=ccs: self.colorIntensityWidgetChangedSlot(colorControlSet, intensity))

        self.lumencorInstance.lampStatesChanged.connect(self.deviceLampStatesChangedSlot)

        self.tempUpdateTimer = QtCore.QTimer(self)
        self.tempUpdateTimer.timeout.connect(self.tempUpdateTimerFiredSlot)
        self.tempUpdateConsecutiveFailures = 0
        self.tempUpdateTimer.start(2000)

    def closeEvent(self, event):
        self.lumencorInstance.disable()
        super().closeEvent(event)
        self.deleteLater()

    def colorEnabledWidgetToggledSlot(self, colorControlSet, on):
        colorControlSet.setEnabled(self.lumencorInstance, on)

    def colorIntensityWidgetChangedSlot(self, colorControlSet, intensity):
        colorControlSet.setPower(self.lumencorInstance, intensity)

    def tempUpdateTimerFiredSlot(self):
        temp = self.lumencorInstance.temperature
        text = str()
        if temp is None:
            text = 'Temp: unavailable'
            self.tempUpdateConsecutiveFailures += 1
            if self.tempUpdateConsecutiveFailures > 3:
                # If the last three temperature queries failed, query temperature only every sixty seconds so as to
                # reduce hitching caused by waiting for blocking read to time out
                self.tempUpdateTimer.start(60000)
        else:
            text = 'Temp: {}ºC'.format(temp)
            if self.tempUpdateConsecutiveFailures > 3:
                # A temperature read finally succeeded.  Revert back to querying every two seconds.
                self.tempUpdateTimer.start(2000)
            self.tempUpdateConsecutiveFailures = 0
        self.ui.tempLabel.setText(text)

    def maxAllLampsSlot(self):
        lampStates = self.lumencorInstance.lampStates
        for ln, ls in lampStates.items():
            ls.power = 255
        self.lumencorInstance.lampStates = lampStates

    def zeroAllLampsSlot(self):
        lampStates = self.lumencorInstance.lampStates
        for ln, ls in lampStates.items():
            ls.power = 0
        self.lumencorInstance.lampStates = lampStates

    def enableAllLampsSlot(self):
        lampStates = self.lumencorInstance.lampStates
        for ln, ls in lampStates.items():
            ls.enabled = True
        self.lumencorInstance.lampStates = lampStates

    def disableAllLampsSlot(self):
        self.lumencorInstance.disable()

    def deviceLampStatesChangedSlot(self, lampStateChanges):
        for name, changes in lampStateChanges.items():
            ccs = self.colorControlSets[name]
            if 'enabled' in changes:
                if changes['enabled']:
                    checkState = QtCore.Qt.Checked
                else:
                    checkState = QtCore.Qt.Unchecked
                ccs.toggle.setCheckState(checkState)
            if 'power' in changes:
                ccs.slider.setValue(changes['power'])
                ccs.spinBox.setValue(changes['power'])

def show(lumencorInstance=None, launcherDescription=None, moduleArgs=None):
    import sys
    import argparse

    parser = argparse.ArgumentParser(launcherDescription)
    parser.add_argument('--port')
    args = parser.parse_args(moduleArgs)

    app = QtWidgets.QApplication(sys.argv)
    if lumencorInstance is None:
        if args.port is None:
            lumencorInstance = Lumencor()
        else:
            lumencorInstance = Lumencor(serialPortDescriptor=args.port)
    dialog = LumencorManipDialog(None, lumencorInstance)
    sys.exit(dialog.exec_())
