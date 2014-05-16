# Copyright 2014 WUSTL ZPLAB

import os
from PyQt5 import QtCore, QtGui, QtWidgets, uic
from acquisition.lumencor.lumencor import Lumencor
from acquisition.lumencor.lumencor_exception import LumencorException

class LumencorManipDialog(QtWidgets.QDialog):
    class ColorControlSet:
        def __init__(self, toggle, slider, spinBox):
            self.toggle = toggle
            self.slider = slider
            self.spinBox = spinBox

    def __init__(self, parent, lumencorInstance):
        super(LumencorManipDialog, self).__init__(parent)
        self.lumencorInstance = lumencorInstance

        # Note that uic.loadUiType(..) returns a tuple containing two class types (the form class and the Qt base
        # class).  The line below instantiates the form class.  It is assumed that the .ui file resides in the same
        # directory as this .py file.
        self.ui = uic.loadUiType(os.path.join(os.path.dirname(__file__), 'direct_manip.ui'))[0]()
        self.ui.setupUi(self)

        self.colorControlSets = {\
            'red' : self.ColorControlSet(self.ui.redToggle, self.ui.redSlider, self.ui.redSpinBox),
            'green' : self.ColorControlSet(self.ui.greenToggle, self.ui.greenSlider, self.ui.greenSpinBox),
            'cyan' : self.ColorControlSet(self.ui.cyanToggle, self.ui.cyanSlider, self.ui.cyanSpinBox),
            'blue' : self.ColorControlSet(self.ui.blueToggle, self.ui.blueSlider, self.ui.blueSpinBox),
            'UV' : self.ColorControlSet(self.ui.UVToggle, self.ui.UVSlider, self.ui.UVSpinBox),
            'teal' : self.ColorControlSet(self.ui.tealToggle, self.ui.tealSlider, self.ui.tealSpinBox) }

        for c, ccs in self.colorControlSets.items():
            # Toggling off a color disables that color's slider and spinbox
            ccs.toggle.toggled.connect(ccs.slider.setEnabled)
            ccs.toggle.toggled.connect(ccs.spinBox.setEnabled)
            # Moving a slider changes the spinbox value
            ccs.slider.valueChanged.connect(ccs.spinBox.setValue)
            # Changes to spinbox move the slider
            ccs.spinBox.valueChanged.connect(ccs.slider.setValue)
            # Handle toggle by color name so color enable/disable command can be sent to lumencor box
            ccs.toggle.toggled.connect(lambda on, name = c: self.handleToggleNamedColor(name, on))
            # Send slider changes to lumencor box
            ccs.slider.sliderMoved.connect(lambda intensity, name = c: self.handleSetNamedColorIntensity(name, intensity))
            # Send spinbox changes to lumencor box unless the spinbox change was caused by a slider drag (slider
            # drag both updates spinbox and sends change to lumencor, so sending change again would be redundant)
            ccs.spinBox.valueChanged.connect(lambda intensity, name = c, slider = ccs.slider: slider.isSliderDown() or self.handleSetNamedColorIntensity(name, intensity))

        self.lumencorInstance.attachObserver(self)
        # Update interface to reflect current state of Lumencor box (which may be something other than default if this dialog was
        # attached to an existing Lumencor instance that has previously been manipulated)
        self.lumencorInstance.forceCompleteLumencorLampStatesChangedNotificationTo(self)

        self.tempUpdateTimer = QtCore.QTimer(self)
        self.tempUpdateTimer.timeout.connect(self.handleTempUpdateTimerFired)
        self.tempUpdateTimer.start(2000)

    def closeEvent(self, event):
        self.lumencorInstance.detachObserver(self)
        self.lumencorInstance.disable()
        super().closeEvent(event)
        self.deleteLater()

    def handleToggleNamedColor(self, name, on):
        exec('self.lumencorInstance.{}Enabled = {}'.format(name, on))

    def handleSetNamedColorIntensity(self, name, intensity):
        exec('self.lumencorInstance.{}Power = {}'.format(name, intensity))

    def handleTempUpdateTimerFired(self):
        temp = self.lumencorInstance.temperature
        text = str()
        if temp is None:
            text = 'Temp: unavailable'
        else:
            text = 'Temp: {}ºC'.format(temp)
        self.ui.tempLabel.setText(text)

    def handleMaxAllLamps(self):
        lampStates = self.lumencorInstance.lampStates
        for ln, ls in lampStates.items():
            ls.power = 255
        self.lumencorInstance.lampStates = lampStates

    def handleZeroAllLamps(self):
        lampStates = self.lumencorInstance.lampStates
        for ln, ls in lampStates.items():
            ls.power = 0
        self.lumencorInstance.lampStates = lampStates

    def handleEnableAllLamps(self):
        lampStates = self.lumencorInstance.lampStates
        for ln, ls in lampStates.items():
            ls.enabled = True
        self.lumencorInstance.lampStates = lampStates

    def handleDisableAllLamps(self):
        self.lumencorInstance.disable()

    def notifyLumencorLampStatesChanged(self, lumencorInstance, lampStateChangesForObserver):
        for name, changes in lampStateChangesForObserver.items():
            ccs = self.colorControlSets[name]
            if 'enabled' in changes:
                if changes['enabled']:
                    checkState = QtCore.Qt.Checked
                else:
                    checkState = QtCore.Qt.Unchecked
                ccs.toggle.setCheckState(checkState)
            if 'power' in changes:
                ccs.slider.setValue(changes['power'])

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
            lumencorInstance = Lumencor(args.port)
    dialog = LumencorManipDialog(None, lumencorInstance)
    sys.exit(dialog.exec_())
