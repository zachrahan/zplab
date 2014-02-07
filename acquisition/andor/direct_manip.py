# Copyright 2014 WUSTL ZPLAB

import os
from PyQt5 import QtCore, QtGui, QtWidgets, uic
from acquisition.andor.andor import Andor
from acquisition.andor.andor_exception import AndorException

class AndorManipMainWindow(QtWidgets.QMainWindow):
    def __init__(self, parent, andorInstance):
        super().__init__(parent)
        self.andorInstance = andorInstance

        self.ui = uic.loadUiType(os.path.join(os.path.dirname(__file__), 'direct_manip.ui'))[0]()
        self.ui.setupUi(self)

        self.graphicsScene = QtWidgets.QGraphicsScene(self)
        self.graphicsScene.setSceneRect(QtCore.QRectF(0, 0, 1000, 1000))
        self.ui.graphicsView.setScene(self.graphicsScene)
        self.imageItem = None

    def closeEvent(self, event):
        super().closeEvent(event)

    def openImageClicked(self):
        fileName, _ = QtWidgets.QFileDialog.getOpenFileName(self)
        if fileName is not None:
            self.usePixmap(QtGui.QPixmap(fileName))

    def saveImageClicked(self):
        pass

    def usePixmap(self, pixmap):
        if self.imageItem is not None:
            self.graphicsScene.removeItem(self.imageItem)
        self.graphicsScene.addPixmap(pixmap)
        self.graphicsScene.setSceneRect(QtCore.QRectF(0, 0, pixmap.width(), pixmap.height()))

def show(andorInstance=None):
    import sys
    app = QtWidgets.QApplication(sys.argv)
    if andorInstance is None:
        andorInstance = Andor()
    mainWindow = AndorManipMainWindow(None, andorInstance)
    mainWindow.show()
    sys.exit(app.exec_())
