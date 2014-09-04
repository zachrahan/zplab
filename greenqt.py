#!/usr/bin/env python3

# The MIT License (MIT)
#
# Copyright (c) 2014 WUSTL ZPLAB
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#
# Authors: Erik Hvatum

import greenlet
from PyQt5 import Qt
import sys
from acquisition.pedals.pedals import Pedals

class WaitDialog(Qt.QDialog):
    def __init__(self, dialog, pedalIdx, mainGt):
        super().__init__(dialog)
        self._dialog = dialog
        self._pedalIdx = pedalIdx
        self._mainGt = mainGt
        self.setWindowModality(Qt.Qt.NonModal)
        self.setWindowTitle('Green Qt Test')
        self.setLayout(Qt.QVBoxLayout())
        self.layout().addWidget(Qt.QLabel('Waiting for pedal {} up...'.format(self._pedalIdx)))
        self._cancelBtn = Qt.QPushButton('cancel')
        self.layout().addWidget(self._cancelBtn)
        self._cancelBtn.clicked.connect(self.cancel)
        self.waitForPedalGt = greenlet.greenlet(self.waitForPedal)

    def waitForPedal(self):
        self._dialog.pedalWaitBtns[self._pedalIdx].setEnabled(False)
        if self._mainGt.switch():
            Qt.QMessageBox.information(self, 'Green Qt Test', 'Pedal {} up received.'.format(self._pedalIdx))
        self._dialog.pedalWaitBtns[self._pedalIdx].setEnabled(True)
        self._dialog.pedalWaitDlgs[self._pedalIdx] = None
        self.close()
        self.destroy()

    def cancel(self):
        self.waitForPedalGt.switch(False)

class Dialog(Qt.QDialog):
    def __init__(self, mainGt):
        super().__init__()
        self._mainGt = mainGt
        self.setWindowTitle('Green Qt Test')
        layout = Qt.QVBoxLayout()
        self.setLayout(layout)

        self.quitButton = Qt.QPushButton('quit')
        layout.addWidget(self.quitButton)
        self.quitButton.clicked.connect(self.close)

        self.pedalWaitBtns = [None, None]
        self.pedalWaitDlgs = [None, None]

        self.pedalWaitBtns[0] = Qt.QPushButton('wait for pedal 0 up')
        layout.addWidget(self.pedalWaitBtns[0])
        self.pedalWaitBtns[0].clicked.connect(lambda: self.pedalWaitBtnClickedSlot(0))

        self.pedalWaitBtns[1] = Qt.QPushButton('wait for pedal 1 up')
        layout.addWidget(self.pedalWaitBtns[1])
        self.pedalWaitBtns[1].clicked.connect(lambda: self.pedalWaitBtnClickedSlot(1))

        self.pedals = Pedals()
        self.pedals.pedalUpChanged.connect(self.pedalUpChangedSlot)

    def pedalWaitBtnClickedSlot(self, pedalIdx):
        if self.pedalWaitDlgs[pedalIdx] is None:
            self.pedalWaitDlgs[pedalIdx] = WaitDialog(self, pedalIdx, self._mainGt)
            self.pedalWaitDlgs[pedalIdx].show()
            self.pedalWaitDlgs[pedalIdx].waitForPedalGt.switch()

    def pedalUpChangedSlot(self, pedalIdx, isUp):
        if isUp and self.pedalWaitDlgs[pedalIdx] is not None:
            self.pedalWaitDlgs[pedalIdx].waitForPedalGt.switch(True)

if __name__ == '__main__':
    app = Qt.QApplication(sys.argv)

    def eventLoop():
        app.exec_()

    eventLoopGt = greenlet.greenlet(eventLoop)
    dialog = Dialog(eventLoopGt)
    dialog.show()
    eventLoopGt.switch()
