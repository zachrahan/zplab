#!/usr/bin/env python

from PyQt5 import Qt
import sys
from ris_widget._ris_widget import RisWidget
from acquisition.root.direct_manip import RootManipDialog
from acquisition.root.root import Root

app = Qt.QApplication(sys.argv)
root = Root()
rootDialog = RootManipDialog(None, root)
rw = RisWidget()

def go():
    rootDialog.show()
    rw.show()
    root.camera.imageAcquired.connect(rw.showImage)

timer = Qt.QTimer()
timer.timeout.connect(go)
timer.setSingleShot(True)
timer.start(100)
app.exec_()

