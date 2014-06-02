#!/usr/bin/env python

from PyQt5 import QtCore, QtGui, QtWidgets
import sys
from acquisition.brightfield_led.brightfield_led import BrightfieldLed
from acquisition.brightfield_led.direct_manip import BrightfieldLedManipDialog
from acquisition.lumencor.lumencor import Lumencor
from acquisition.lumencor.direct_manip import LumencorManipDialog

app = QtWidgets.QApplication(sys.argv)

md = QtWidgets.QDialog()
md.setLayout(QtWidgets.QHBoxLayout())

l = Lumencor()
ld = LumencorManipDialog(md, l)
ld.setWindowFlags(QtCore.Qt.FramelessWindowHint)
ld.setFocusPolicy(QtCore.Qt.NoFocus)
md.layout().addWidget(ld)

b = BrightfieldLed()
bd = BrightfieldLedManipDialog(md, b)
bd.setWindowFlags(QtCore.Qt.FramelessWindowHint)
bd.setFocusPolicy(QtCore.Qt.NoFocus)
md.layout().addWidget(bd)

md.show()
exit(app.exec_())
