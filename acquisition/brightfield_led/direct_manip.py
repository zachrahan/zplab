# Copyright 2014 WUSTL ZPLAB
# Erik Hvatum (ice.rikh@gmail.com)

import os
from PyQt5 import QtCore, QtGui, QtWidgets, uic
from acquisition.brightfield_led.brightfield_led import BrightfieldLed

class BrightfieldLedManipDialog(QtWidgets.QDialog):
    def __init__(self, parent, brightfieldLedInstance):
        super().__init__(parent)
        self.brightfieldLedInstance = brightfieldLedInstance

        # Note that uic.loadUiType(..) returns a tuple containing two class types (the form class and the Qt base
        # class).  The line below instantiates the form class.  It is assumed that the .ui file resides in the same
        # directory as this .py file.
        self.ui = uic.loadUiType(os.path.join(os.path.dirname(__file__), 'direct_manip.ui'))[0]()
        self.ui.setupUi(self)

        self.brightfieldLedInstance.enabledChanged.connect(self.deviceEnabledChangedSlot)
        self.brightfieldLedInstance.powerChanged.connect(self.devicePowerChangedSlot)

        self.deviceEnabledChangedSlot(self.brightfieldLedInstance.enabled)
        self.devicePowerChangedSlot(self.brightfieldLedInstance.power)

    def closeEvent(self, event):
        self.brightfieldLedInstance.enabled = False
        super().closeEvent(event)
        self.deleteLater()

    def enabledToggledSlot(self, enabled):
        self.brightfieldLedInstance.enabled = enabled

    def powerSpinBoxValueChangedSlot(self, power):
        # Note: notice that this spinbox change handler does not adjust the slider.  How, then, does the slider move
        # so that it tracks the spinbox?  Changing brightfieldLedInstance's power property causes the
        # brightfieldLedInstance to emit its powerChanged signal.  devicePowerChangedSlot is connected to this signal,
        # and as you can see, it updates both the sliders and the spinbox.  This doesn't cause another update cycle to
        # happen as spinbox's value doesn't actually change - it is redundantly set to the value it was just changed to,
        # and Qt recognizes this and doesn't emit its valueChanged signal.
        self.brightfieldLedInstance.power = power

    def powerSliderValueChangedSlot(self, power):
        self.brightfieldLedInstance.power = power

    def devicePowerChangedSlot(self, power):
        self.ui.powerSlider.setValue(power)
        self.ui.powerSpinBox.setValue(power)

    def deviceEnabledChangedSlot(self, enabled):
        self.ui.enabledToggle.setCheckState(QtCore.Qt.Checked if enabled else QtCore.Qt.Unchecked)
        self.ui.powerSlider.setEnabled(enabled)
        self.ui.powerSpinBox.setEnabled(enabled)

def show(brightfieldLedInstance=None, launcherDescription=None, moduleArgs=None):
    import sys
    import argparse

    parser = argparse.ArgumentParser(launcherDescription)
    parser.add_argument('--port')
    args = parser.parse_args(moduleArgs)

    app = QtWidgets.QApplication(sys.argv)
    if brightfieldLedInstance is None:
        if args.port is None:
            brightfieldLedInstance = BrightfieldLed()
        else:
            brightfieldLedInstance = BrightfieldLed(serialPortDescriptor=args.port)
    dialog = BrightfieldLedManipDialog(None, brightfieldLedInstance)
    sys.exit(dialog.exec_())
