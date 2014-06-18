#!/usr/bin/env python

from PyQt5 import Qt
import sys
from acquisition.andor.andor import Camera
from acquisition.andor.direct_manip import CameraManipDialog
from acquisition.brightfield_led.brightfield_led import BrightfieldLed
from acquisition.brightfield_led.direct_manip import BrightfieldLedManipDialog
from acquisition.lumencor.lumencor import Lumencor
from acquisition.lumencor.direct_manip import LumencorManipDialog

app = Qt.QApplication(sys.argv)

multiManip = Qt.QDialog()
multiManip.setLayout(Qt.QHBoxLayout())

def addDirectManip(deviceType, manipType):
    device = deviceType()
    groupBox = Qt.QGroupBox(multiManip)
    multiManip.layout().addWidget(groupBox)
    groupBox.setLayout(Qt.QHBoxLayout())
    manip = manipType(groupBox, device)
    groupBox.setTitle(manip.windowTitle())
    manip.setWindowFlags(Qt.Qt.FramelessWindowHint)
    manip.setFocusPolicy(Qt.Qt.NoFocus)
    groupBox.layout().addWidget(manip)

addDirectManip(Lumencor, LumencorManipDialog)
addDirectManip(BrightfieldLed, BrightfieldLedManipDialog)
addDirectManip(Camera, CameraManipDialog)

multiManip.show()
exit(app.exec_())
