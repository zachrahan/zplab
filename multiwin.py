#!/usr/bin/env python

from PyQt5 import QtCore, QtGui, QtWidgets
import sys
from acquisition.brightfield_led.brightfield_led import BrightfieldLed
from acquisition.brightfield_led.direct_manip import BrightfieldLedManipDialog
from acquisition.lumencor.direct_manip import LumencorManipDialog
from acquisition.lumencor.lumencor import Lumencor

app = QtWidgets.QApplication(sys.argv)

l = Lumencor()
ld = LumencorManipDialog(None, l)
ld.show()

b = BrightfieldLed()
bd = BrightfieldLedManipDialog(None, b)
bd.show()

exit(app.exec_())
