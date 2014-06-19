#!/usr/bin/env python

import numpy
from PyQt5 import Qt
import sys
from ris_widget._ris_widget import RisWidget
from acquisition.root.direct_manip import RootManipDialog
from acquisition.root.root import Root

app = Qt.QApplication(sys.argv)
root = Root()
rootDialog = RootManipDialog(None, root)
rw = RisWidget()
timer = Qt.QTimer()

def start():
    timer.timeout.disconnect()
    timer.timeout.connect(stop)
    timer.start(60 * 60 * 1000)
    root.camera.startAcquisitionSequence()

def stop():
    timer.timeout.disconnect()
    root.camera.stopAcquisitionSequence()
    timer.timeout.connect(save)
    timer.start(100)

def save():
    numpy.save('/home/ehvatum/waits.npy', numpy.array([[i[0], i[1], i[2]] for i in root.camera.waits]))
    sys.exit()

def go():
    timer.timeout.disconnect()
    rootDialog.show()
    rw.show()
#   root.camera.imageAcquired.connect(rw.showImage)
    root.camera.rw = rw
    root.camera.cycleMode = root.camera.CycleMode.Continuous
    root.camera.frameRate = 18.0
    timer.timeout.connect(start)
    timer.start(1000)

timer.timeout.connect(go)
timer.setSingleShot(True)
timer.start(100)
app.exec_()

