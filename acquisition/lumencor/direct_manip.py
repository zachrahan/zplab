from PyQt5 import QtCore, QtGui, QtWidgets
from acquisition.lumencor.ui_lumencormanipdialog import Ui_LumencorManipDialog

class LumencorManipDialog(QtWidgets.QDialog):
    class ColorControlSet:
        def __init__(self, toggle, slider, spinBox):
            self.toggle = toggle
            self.slider = slider
            self.spinBox = spinBox

    def __init__(self, parent=None):
        super(LumencorManipDialog, self).__init__(parent)

        self.ui = Ui_LumencorManipDialog()
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
            # Send spinbox changed to lumencor box unless the spinbox change was caused by a slider drag
            ccs.spinBox.valueChanged.connect(lambda intensity, name = c, slider = ccs.slider: slider.isSliderDown() or self.handleSetNamedColorIntensity(name, intensity))

    def handleToggleNamedColor(self, name, on):
        print('toggled {} {}'.format(name, on))

    def handleSetNamedColorIntensity(self, name, intensity):
        print('set {} intensity to {}'.format(name, intensity))

def show():
    import sys
    app = QtWidgets.QApplication(sys.argv)
    dialog = LumencorManipDialog()
    sys.exit(dialog.exec_())
