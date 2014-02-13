# Copyright 2014 WUSTL ZPLAB

import numpy as np
import numpy.matlib
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

        self.enableWhenConnected = [
            self.ui.testButton,
            self.ui.exposureTimeLabel,
            self.ui.exposureTimeSpinBox,
            self.ui.acquireButton ]
        self.disableWhenConnected = [
            self.ui.andorDeviceListCombo,
            self.ui.refreshAndorDeviceListButton ]

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
            for widget in self.enableWhenConnected:
                widget.setEnabled(True)
            for widget in self.disableWhenConnected:
                widget.setEnabled(False)
            self.ui.connectDisconnectAndorDeviceButton.setText('Disconnect')
        else:
            # Disconnect...
            self.zylaInstance = None
            for widget in self.enableWhenConnected:
                widget.setEnabled(False)
            for widget in self.disableWhenConnected:
                widget.setEnabled(True)
            self.ui.connectDisconnectAndorDeviceButton.setText('Connect')

    def testButtonClicked(self):
        QtWidgets.QMessageBox.information(self, 'Test Result', self.zylaInstance.getPixelEncoding())

    def acquireButtonClicked(self):
        im16g = self.zylaInstance.acquireImage(self.ui.exposureTimeSpinBox.value())
        # Normalize
        im16gf = im16g.astype(np.float32)
        #im16gf = np.matlib.rand(im16g.shape).view(np.ndarray)
        im16gf -= im16gf.min()
        im16gf /= im16gf.max()
        del im16g
        # Display (SLOW)
        imq = QtGui.QImage(im16gf.shape[1], im16gf.shape[0], QtGui.QImage.Format_RGB32)
        for y in range(im16gf.shape[0]):
            for x in range(im16gf.shape[1]):
                cv = im16gf[y, x] * 256
                imq.setPixel(x, y, QtGui.qRgb(cv, cv, cv))
        self._usePixmap(QtGui.QPixmap.fromImage(imq))

def show(launcherDescription=None, moduleArgs=None, andorInstance=None):
    import sys
    app = QtWidgets.QApplication(sys.argv)
    if andorInstance is None:
        andorInstance = Andor()
    mainWindow = AndorManipMainWindow(None, andorInstance)
    mainWindow.show()
    sys.exit(app.exec_())
