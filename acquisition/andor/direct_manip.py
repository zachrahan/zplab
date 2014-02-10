# Copyright 2014 WUSTL ZPLAB

import os
from PyQt5 import QtCore, QtGui, QtWidgets, uic
from acquisition.andor.andor import (Andor, Zyla)
from acquisition.andor.andor_exception import AndorException

class AndorManipMainWindow(QtWidgets.QMainWindow):
    def __init__(self, parent, andorInstance):
        super().__init__(parent)
        self.andorInstance = andorInstance
        self.zylaInstance = None

        self.ui = uic.loadUiType(os.path.join(os.path.dirname(__file__), 'direct_manip.ui'))[0]()
        self.ui.setupUi(self)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)

        self.graphicsScene = QtWidgets.QGraphicsScene(self)
        self.graphicsScene.setSceneRect(QtCore.QRectF(0, 0, 1000, 1000))
        self.ui.graphicsView.setScene(self.graphicsScene)
        self.imageItem = None

    def closeEvent(self, event):
        super().closeEvent(event)

    def openImageClicked(self):
        fileName, _ = QtWidgets.QFileDialog.getOpenFileName(self)
        if fileName is not None:
            self._usePixmap(QtGui.QPixmap(fileName))

    def saveImageClicked(self):
        pass

    def _usePixmap(self, pixmap):
        if self.imageItem is not None:
            self.graphicsScene.removeItem(self.imageItem)
        self.graphicsScene.addPixmap(pixmap)
        self.graphicsScene.setSceneRect(QtCore.QRectF(0, 0, pixmap.width(), pixmap.height()))

    def refreshAndorDeviceListButtonClicked(self):
        deviceNames = self.andorInstance.getDeviceNames()
        # Clear existing contents
        while self.ui.andorDeviceListCombo.count() > 0:
            self.ui.andorDeviceListCombo.removeItem(self.ui.andorDeviceListCombo.count() - 1)
        if deviceNames is None or len(deviceNames) == 0:
            self.ui.andorDeviceListCombo.setEnabled(False)
            self.ui.connectDisconnectAndorDeviceButton.setEnabled(False)
        else:
            # Populate
            deviceIndex = 0
            for deviceName in deviceNames:
                self.ui.andorDeviceListCombo.addItem('{}: {}'.format(deviceIndex, deviceName))
                deviceIndex += 1
            self.ui.andorDeviceListCombo.setEnabled(True)
            self.ui.connectDisconnectAndorDeviceButton.setEnabled(True)

    def connectDisconnectAndorDeviceButtonClicked(self):
        if self.zylaInstance is None:
            # Connect...
            self.zylaInstance = Zyla(self.andorInstance, self.ui.andorDeviceListCombo.currentIndex())
            self.ui.andorDeviceListCombo.setEnabled(False)
            self.ui.refreshAndorDeviceListButton.setEnabled(False)
            self.ui.connectDisconnectAndorDeviceButton.setText('Disconnect')
            self.ui.testButton.setEnabled(True)
        else:
            # Disconnect...
            self.zylaInstance = None
            self.ui.andorDeviceListCombo.setEnabled(True)
            self.ui.refreshAndorDeviceListButton.setEnabled(True)
            self.ui.connectDisconnectAndorDeviceButton.setText('Connect')
            self.ui.testButton.setEnabled(False)

    def testButtonClicked(self):
        QtWidgets.QMessageBox.information(self, 'Test Result', self.zylaInstance.getPixelEncoding())

def show(andorInstance=None):
    import sys
    app = QtWidgets.QApplication(sys.argv)
    if andorInstance is None:
        andorInstance = Andor()
    mainWindow = AndorManipMainWindow(None, andorInstance)
    mainWindow.show()
    sys.exit(app.exec_())
