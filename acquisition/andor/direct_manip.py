# Copyright 2014 WUSTL ZPLAB

import ctypes as ct
import numpy as np
from OpenGL import GL
import os
from PyQt5 import QtCore, QtGui, QtWidgets, QtOpenGL, uic
from acquisition.andor.andor import Camera
from acquisition.andor.andor_exception import AndorException

class ImageItem(QtWidgets.QGraphicsItem):
    def __init__(self, pixmap, parent = None):
        super().__init__(parent)
        self.pixmap = pixmap
        self.textureId = None
        self.boundingQRectF = QtCore.QRectF(0, 0, self.pixmap.width(), self.pixmap.height())

    def boundingRect(self):
        return self.boundingQRectF

    def paint(self, painter, option, widget):
        if widget is None:
            raise AndorException('ImageItem cache mode must be QGraphicsItem::NoCache.')
        painter.beginNativePainting()
        if self.textureId is None:
            self.textureId = widget.bindTexture(self.pixmap)
        widget.drawTexture(self.boundingQRectF, self.textureId)
        painter.endNativePainting()

class AndorManipMainWindow(QtWidgets.QMainWindow):
    def __init__(self, parent):
        super().__init__(parent)
        self.settings = QtCore.QSettings('PincusLab', 'acquisition.andor.direct_manip')
        self.camera = None

        self.ui = uic.loadUiType(os.path.join(os.path.dirname(__file__), 'direct_manip.ui'))[0]()
        self.ui.setupUi(self)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)

        qglf = QtOpenGL.QGLFormat()
        # Our weakest target platform is Macmini6,1 which has Intel HD 4000 graphics supporting up to OpenGL 4.1 on OS X
        qglf.setVersion(4, 3)
        # QGraphicsView uses at least some OpenGL functionality deprecated in OpenGL 3.0 when manipulating the surface
        # owned by the QGLWidget
        qglf.setProfile(QtOpenGL.QGLFormat.CompatibilityProfile)
        # Uncomment following line if tearing is visible in graphics view widget
#       qglf.setSwapInterval(1)
        # Want hardware rendering (should be enabled by default, but this can't hurt)
        qglf.setDirectRendering(True)
        # Force graphicsview to render with OpenGL backend
        self.ui.graphicsView.setViewport(QtOpenGL.QGLWidget(qglf))

        self.graphicsScene = QtWidgets.QGraphicsScene(self)
        self.graphicsScene.setSceneRect(QtCore.QRectF(0, 0, 100, 100))
        self.ui.graphicsView.setScene(self.graphicsScene)
        self.imageItem = None
        self.ui.graphicsView.setDragMode(QtWidgets.QGraphicsView.ScrollHandDrag)

        self.enableWhenConnected = [
            self.ui.testButton,
            self.ui.exposureTimeLabel,
            self.ui.exposureTimeSpinBox,
            self.ui.acquireButton ]
        self.disableWhenConnected = [
            self.ui.andorDeviceListCombo,
            self.ui.refreshAndorDeviceListButton ]

        self.restoreSettings()

    def closeEvent(self, event):
        self.saveSettings()
        super().closeEvent(event)

    def saveSettings(self):
        self.settings.beginGroup("mainwindow")
        self.settings.setValue("save name", self.fileName)
        self.settings.setValue("save path", self.filePath)
        if self.isMaximized():
            self.settings.setValue("maximized", true);
            self.settings.remove("size");
            self.settings.remove("pos");
        else:
            self.settings.remove("maximized");
            self.settings.setValue("size", self.size());
            self.settings.setValue("pos", self.pos());
        self.settings.endGroup()

    def restoreSettings(self):
        self.settings.beginGroup("mainwindow")
        self.fileName = self.settings.value("save name", "")
        self.filePath = self.settings.value("save path", "")
        if self.settings.contains("maximized") and self.settings.value("maximized"):
            self.showMaximized()
        elif self.settings.contains("size") and type(self.settings.value("size")) is QtCore.QSize \
         and self.settings.contains("pos") and type(self.settings.value("pos")) is QtCore.QPoint:
            s = self.settings.value("size")
            p = self.settings.value("pos")
            r = QtCore.QRect(p, s)
            dt = QtWidgets.QApplication.desktop()
            # Only restore window geometry if the restored window would be completely on screen, avoiding the annoying
            # scenario where the program was used on the bottom left of a large monitor attached to a laptop and then later
            # started on the smaller laptop screen, causing the program window to be offscreen entirely.
            for si in range(dt.screenCount()):
                if dt.screenGeometry(si).contains(r):
                    self.move(p)
                    self.resize(s)
                    break
        self.settings.endGroup()

    def openImageClicked(self):
        fileName, _ = QtWidgets.QFileDialog.getOpenFileName(self)
        if fileName is not None and fileName != '':
            impx = QtGui.QPixmap(fileName)
            if impx.isNull():
                QtWidgets.QMessageBox.critical(self, 'Failed to Load Image', 'Failed to load an image from "{}".'.format(fileName))
            else:
                fi = QtCore.QFileInfo(fileName)
                self.filePath = fi.absolutePath()
                self.fileName = fi.fileName()
                self._usePixmap(impx)

    def saveImageClicked(self):
        pass

    def _usePixmap(self, pixmap):
        if self.imageItem is not None:
            self.graphicsScene.removeItem(self.imageItem)
            self.imageItem = None
        self.imageItem = ImageItem(pixmap)
        self.graphicsScene.addItem(self.imageItem)
        self.graphicsScene.setSceneRect(QtCore.QRectF(0, 0, pixmap.width(), pixmap.height()))

    def refreshAndorDeviceListButtonClicked(self):
        deviceNames = Camera.getDeviceNames()
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
        if self.camera is None:
            # Connect...
            self.camera = Camera(self.ui.andorDeviceListCombo.currentIndex())
            for widget in self.enableWhenConnected:
                widget.setEnabled(True)
            for widget in self.disableWhenConnected:
                widget.setEnabled(False)
            self.ui.connectDisconnectAndorDeviceButton.setText('Disconnect')
        else:
            # Disconnect...
            self.camera = None
            for widget in self.enableWhenConnected:
                widget.setEnabled(False)
            for widget in self.disableWhenConnected:
                widget.setEnabled(True)
            self.ui.connectDisconnectAndorDeviceButton.setText('Connect')

    def testButtonClicked(self):
        QtWidgets.QMessageBox.information(self, 'Test Result', self.camera.getPixelEncoding())

    def acquireButtonClicked(self):
        im16g = self.camera.acquireImage(self.ui.exposureTimeSpinBox.value())
        shape = im16g.shape

        # Normalize and convert to 8-bit grayscale
        im16gf = im16g.astype(np.float32)
        del im16g
        im16gf -= im16gf.min()
        im16gf *= 0xff / im16gf.max()
        im32argb = im16gf.astype(np.uint8)
        del im16gf

        # Convert to 32-bit color with ignored junk data in alpha channel
        im32argb = np.repeat(im32argb, 4, axis=1)

        # Display
        imq = QtGui.QImage(im32argb.data, shape[1], shape[0], QtGui.QImage.Format_RGB32)
        impx = QtGui.QPixmap.fromImage(imq)
        # It should not be necessary to call detach here, but if this is not done, impx will continue
        # to reference im32argb through imq - without increasing the reference count of either.  According
        # to the Qt docs, QPixmap.fromImage copies the QImage's data, but this does not seem to actually
        # be the case.  Perhaps Qt is too clever for its own good and inserts im32argb into the pixmap cache;
        # calling detach forces QPixmap to copy its data out of the pixmap cache and thus works around the
        # issue.
        impx.detach()
        del imq
        del im32argb
        self._usePixmap(impx)
        del impx



def show(launcherDescription=None, moduleArgs=None):
    import sys
    app = QtWidgets.QApplication(sys.argv)
    mainWindow = AndorManipMainWindow(None)
    mainWindow.show()
    sys.exit(app.exec_())
