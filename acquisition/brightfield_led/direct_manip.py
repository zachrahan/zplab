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

        self.brightfieldLedInstance.attachObserver(self)
        self.brightfieldLedInstance.forceComprehensiveObserverNotification(self)

    def closeEvent(self, event):
        self.brightfieldLedInstance.detachObserver(self)
        self.brightfieldLedInstance.enabled = False
        super().closeEvent(event)
        self.deleteLater()

    def enabledToggledSlot(self, enabled):
        self.brightfieldLedInstance.enabled = enabled

    def powerSpinBoxValueChangedSlot(self, power):
        self.brightfieldLedInstance.power = power

    def powerSliderValueChangedSlot(self, power):
        self.brightfieldLedInstance.power = power

    def notifyBrightfieldLedEnablementChanged(self, brightfieldLedInstance, enabled):
        self.ui.enabledToggle.setCheckState(QtCore.Qt.Checked if enabled else QtCore.Qt.Unchecked)
        self.ui.powerSlider.setEnabled(enabled)
        self.ui.powerSpinBox.setEnabled(enabled)

    def notifyBrightfieldLedPowerChanged(self, brightfieldLedInstance, power):
        self.ui.powerSlider.setValue(power)
        self.ui.powerSpinBox.setValue(power)

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
            brightfieldLedInstance = BrightfieldLed(args.port)
    dialog = BrightfieldLedManipDialog(None, brightfieldLedInstance)
    sys.exit(dialog.exec_())
