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
            'red' : self.ColorControlSet(self.ui.redToggle, self.ui.redSlider, self.ui.redSpinBox),\
            'green' : self.ColorControlSet(self.ui.greenToggle, self.ui.greenSlider, self.ui.greenSpinBox),\
            'cyan' : self.ColorControlSet(self.ui.cyanToggle, self.ui.cyanSlider, self.ui.cyanSpinBox),\
            'blue' : self.ColorControlSet(self.ui.blueToggle, self.ui.blueSlider, self.ui.blueSpinBox),\
            'UV' : self.ColorControlSet(self.ui.UVToggle, self.ui.UVSlider, self.ui.UVSpinBox),\
            'teal' : self.ColorControlSet(self.ui.tealToggle, self.ui.tealSlider, self.ui.tealSpinBox) }

        for c, ccs in self.colorControlSets.items():
            # Toggling off a color disables that color's slider and spinbox
            ccs.toggle.toggled.connect(ccs.slider.setEnabled)
            ccs.toggle.toggled.connect(ccs.spinBox.setEnabled)
            # Moving a slider changes the spinbox value
            ccs.slider.sliderMoved.connect(ccs.spinBox.setValue)
            # Changes to spinbox move the slider
            ccs.spinBox.valueChanged.connect(ccs.slider.setValue)
            # Handle toggle by color name so color enable/disable command can be sent to lumencor box
            ccs.toggle.toggled.connect(lambda on, name = c: self.handleToggleNamedColor(name, on))
            # Send slider changes to lumencor box
            ccs.slider.sliderMoved.connect(lambda intensity, name = c: self.handleSetNamedColorIntensity(name, intensity))
            # Send spinbox changes to lumencor box unless the spinbox change was caused by a slider drag (slider
            # drag both updates spinbox and sends change to lumencor, so sending change again would be redundant)
            ccs.spinBox.valueChanged.connect(lambda intensity, name = c, slider = ccs.slider: slider.isSliderDown() or self.handleSetNamedColorIntensity(name, intensity))

        self.tempUpdateTimer = QtCore.QTimer(self)
        self.tempUpdateTimer.timeout.connect(self.handleTempUpdateTimerFired)
        self.tempUpdateTimer.start(2000)

    def closeEvent(self, event):
        self.lumencorInstance.toggleAllColors(False)
        super().closeEvent(event)

    def handleToggleNamedColor(self, name, on):
        self.lumencorInstance.toggleColor(name, on)

    def handleSetNamedColorIntensity(self, name, intensity):
        self.lumencorInstance.setColorIntensity(name, intensity)

    def handleTempUpdateTimerFired(self):
        temp = self.lumencorInstance.getTemp()
        text = str()
        if temp is None:
            text = 'Temp: unavailable'
        else:
            text = 'Temp: {}ºC'.format(temp)
        self.ui.tempLabel.setText(text)

def show(lumencorInstance=None):
    import sys
    app = QtWidgets.QApplication(sys.argv)
    if lumencorInstance is None:
        lumencorInstance = Lumencor()
    dialog = LumencorManipDialog(None, lumencorInstance)
    sys.exit(dialog.exec_())
