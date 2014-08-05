# Copyright 2014 WUSTL ZPLAB
# Erik Hvatum (ice.rikh@gmail.com)

from PyQt5 import Qt
from acquisition.andor.direct_manip import CameraManipDialog
from acquisition.brightfield_led.direct_manip import BrightfieldLedManipDialog
from acquisition.lumencor.direct_manip import LumencorManipDialog
from acquisition.root.root import Root

class RootManipDialog(Qt.QDialog):
    def __init__(self, parent, rootInstance):
        super().__init__(parent)
        self.rootInstance = rootInstance
        layout = Qt.QHBoxLayout()
        self.setLayout(layout)

        def addDirectManip(rootSubdeviceName):
            dialogClassName = rootSubdeviceName[0].upper() + rootSubdeviceName[1:] + 'ManipDialog'
            execstr = 'self.{0}GroupBox = Qt.QGroupBox(self)\n'
            execstr+= 'layout.addWidget(self.{0}GroupBox)\n'
            execstr+= 'self.{0}GroupBox.setLayout(Qt.QHBoxLayout())\n'
            execstr+= 'self.{0}Dialog = DialogClass(self.{0}GroupBox, self.rootInstance.{0})\n'
            execstr+= 'self.{0}GroupBox.setTitle(self.rootInstance.{0}.deviceName)\n'
            execstr+= 'self.{0}Dialog.setWindowFlags(Qt.Qt.FramelessWindowHint)\n'
            execstr+= 'self.{0}Dialog.setFocusPolicy(Qt.Qt.NoFocus)\n'
            execstr+= 'self.{0}GroupBox.layout().addWidget(self.{0}Dialog)'
            exec(execstr.format(rootSubdeviceName), {'self':self, 'Qt':Qt, 'layout':layout, 'DialogClass':eval(dialogClassName)})
        
        addDirectManip('lumencor')
        addDirectManip('brightfieldLed')
        addDirectManip('camera')

def show(rootInstance=None, launcherDescription=None, moduleArgs=None):
    import sys

    app = Qt.QApplication(sys.argv)
    if rootInstance is None:
        rootInstance = Root()
    dialog = RootManipDialog(None, rootInstance)
    sys.exit(dialog.exec_())
