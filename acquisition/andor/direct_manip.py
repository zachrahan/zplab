# Copyright 2014 WUSTL ZPLAB

import ctypes as ct
import numpy as np
from OpenGL import GL
import os
from PyQt5 import QtCore, QtGui, QtWidgets, QtOpenGL, uic
import sys
import threading
import time
from acquisition.andor.andor import Camera
from acquisition.andor.andor_exception import AndorException

class ImageItem(QtWidgets.QGraphicsItem):
    def __init__(self, pixmap_, parent = None):
        super().__init__(parent)
        self.pixmap = pixmap_
        self.textureId = None
        self.textureIsStale = True
        self.boundingQRectF = QtCore.QRectF(0, 0, self.pixmap.width(), self.pixmap.height())

    def boundingRect(self):
        return self.boundingQRectF

    def updateImage(self, pixmap_):
        self.pixmap = pixmap_
        self.textureIsStale = True
        newBoundingQRectF = QtCore.QRectF(0, 0, self.pixmap.width(), self.pixmap.height())
        if self.boundingQRectF != newBoundingQRectF:
            self.prepareGeometryChange()
            self.boundingQRectF = newBoundingQRectF
        self.update()

    def paint(self, painter, option, widget):
        if widget is None:
            raise AndorException('ImageItem cache mode must be QGraphicsItem::NoCache.')
        painter.beginNativePainting()
        if self.textureIsStale:
            if self.textureId is not None:
                widget.deleteTexture(self.textureId)
            self.textureId = widget.bindTexture(self.pixmap)
            self.textureIsStale = False
        widget.drawTexture(self.boundingQRectF, self.textureId)
        painter.endNativePainting()

class SingleImageAcquisitionThread(QtCore.QThread):
    def __init__(self, andorManipMainWindow_):
        super().__init__()
        self.andorManipMainWindow = andorManipMainWindow_

    def run(self):
        succeeded = None
        try:
            self.im16g = self.andorManipMainWindow.camera.acquireImage()
            succeeded = True
        except AndorException as e:
            print(e, file=sys.stderr)
            succeeded = False
        self.andorManipMainWindow.singleImageAcquiredSignal.emit(succeeded)

class LiveAcquisitionThread(QtCore.QThread):
    def __init__(self, andorManipMainWindow_, bufferCount_):
        super().__init__()
        self.andorManipMainWindow = andorManipMainWindow_
        self.bufferCount = bufferCount_
        self.stop = False
        self.bufferDeQueueCount = 0
        self.bufferReQueue = []
        self.bufferReQueueLock = threading.Lock()
        self.bufferReQueued = threading.Condition(self.bufferReQueueLock)

    def reQueueBuffer(self, buffer):
        with self.bufferReQueueLock:
            self.bufferReQueue.append(buffer)
            self.bufferReQueued.notify()

    def run(self):
        camera = self.andorManipMainWindow.camera
        self.aoih = camera.AT_GetInt(camera.Feature.AOIHeight)
        self.aoiw = camera.AT_GetInt(camera.Feature.AOIWidth)
        buffers = [camera.makeAcquisitionBuffer() for x in range(self.bufferCount)]
        self.bufferIdsToBuffers = {b.ctypes.data_as(ct.c_void_p).value: b for b in buffers}
        camera.AT_Flush()
        camera.AT_SetEnumString(camera.Feature.CycleMode, 'Continuous')
        camera.AT_SetEnumString(camera.Feature.TriggerMode, 'Software')
        for buffer in buffers:
            camera.AT_QueueBuffer(buffer)
        camera.AT_Command(camera.Feature.AcquisitionStart)
        while not self.stop:
            # Re-queue any of our buffers that the main thread has finished reading.  If we have no buffers left and
            # the main thread has not requeued any, we wait for the main thread to do so.
            with self.bufferReQueueLock:
                if self.bufferDeQueueCount == self.bufferCount:
                    while not self.bufferReQueue:
                        self.bufferReQueued.wait()
                while self.bufferReQueue:
                    camera.AT_QueueBuffer(self.bufferReQueue.pop())
                    self.bufferDeQueueCount -= 1
            # Hopefully avoid waitbuffer timeout due to exposure time increasing during live acquisition
            acquisitionTimeout = int(camera.AT_GetFloat(camera.Feature.ExposureTime) * 3 * 1000)
            if acquisitionTimeout < 500:
                acquisitionTimeout = 500
            try:
                camera.AT_Command(camera.Feature.SoftwareTrigger)
                acquiredBufferId = camera.AT_WaitBuffer(acquisitionTimeout)
                self.bufferDeQueueCount += 1
            except AndorException as e:
                acquiredBufferId = -1
                print(e, file=sys.stderr)
            self.andorManipMainWindow.liveImageAcquiredSignal.emit([acquiredBufferId])
        camera.AT_Command(camera.Feature.AcquisitionStop)
        camera.AT_Flush()
        self.andorManipMainWindow.liveAcquisitionEndedSignal.emit()

class AndorManipMainWindow(QtWidgets.QMainWindow):
    singleImageAcquiredSignal = QtCore.pyqtSignal(bool)
    liveImageAcquiredSignal = QtCore.pyqtSignal(list)
    liveAcquisitionEndedSignal = QtCore.pyqtSignal()

    def __init__(self, parent):
        super().__init__(parent)
        self.settings = QtCore.QSettings('PincusLab', 'acquisition.andor.direct_manip')
        self.camera = None
        self.isLiveAcquiring = False

        self.ui = uic.loadUiType(os.path.join(os.path.dirname(__file__), 'direct_manip.ui'))[0]()
        self.ui.setupUi(self)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)

        qglf = QtOpenGL.QGLFormat()
        # Our weakest target platform is Macmini6,1 which has Intel HD 4000 graphics supporting up to OpenGL 4.1 on OS X
        qglf.setVersion(4, 1)
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
            self.ui.actualExposureTimeLabel,
            self.ui.actualExposureTimeLcdDisplay,
            self.ui.acquireButton,
            self.ui.liveStreamBufferCountLabel,
            self.ui.liveStreamBufferCountSpinBox,
            self.ui.startStopLiveStreamButton ]
        self.disableWhenConnected = [
            self.ui.andorDeviceListCombo,
            self.ui.refreshAndorDeviceListButton ]

        self.singleImageAcquiredSignal.connect(self.singleImageAcquired, QtCore.Qt.QueuedConnection)
        self.liveImageAcquiredSignal.connect(self.liveImageAcquired, QtCore.Qt.QueuedConnection)
        self.liveAcquisitionEndedSignal.connect(self.liveAcquisitionEnded, QtCore.Qt.QueuedConnection)

        self.restoreSettings()

    def closeEvent(self, event):
        self.saveSettings()
        super().closeEvent(event)

    def saveSettings(self):
        self.settings.beginGroup("mainwindow")
        self.settings.setValue("save name", self.fileName)
        self.settings.setValue("save path", self.filePath)
        if self.isMaximized():
            self.settings.setValue("maximized", True);
            self.settings.remove("size")
            self.settings.remove("pos")
        else:
            self.settings.remove("maximized");
            self.settings.setValue("size", self.size())
            self.settings.setValue("pos", self.pos())
        self.settings.setValue("exposure", self.ui.exposureTimeSpinBox.value())
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
        self.ui.exposureTimeSpinBox.setValue(float(self.settings.value("exposure", 0.1)))
        self.settings.endGroup()

    def openImageClicked(self):
        fileName, _ = QtWidgets.QFileDialog.getOpenFileName(self, 'Open image', self.filePath)
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
        if self.imageItem is None:
            self.imageItem = ImageItem(pixmap)
            self.graphicsScene.addItem(self.imageItem)
        else:
            self.imageItem.updateImage(pixmap)
        self.graphicsScene.setSceneRect(QtCore.QRectF(0, 0, pixmap.width(), pixmap.height()))

    def _display16BitGrayscale(self, im16g):
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
            self.exposureTimeSpinBoxChanged(self.ui.exposureTimeSpinBox.value())
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

    def exposureTimeSpinBoxChanged(self, exposureTime):
        if self.camera is not None:
            actual = self.camera.setExposureTime(exposureTime)
            self.ui.actualExposureTimeLcdDisplay.display(actual)

    def acquireButtonClicked(self):
        self.ui.connectDisconnectAndorDeviceButton.setEnabled(False)
        self.ui.acquireButton.setEnabled(False)
        self.ui.liveStreamBufferCountLabel.setEnabled(False)
        self.ui.liveStreamBufferCountSpinBox.setEnabled(False)
        self.ui.startStopLiveStreamButton.setEnabled(False)
        self.singleImageAcquisitionThread = SingleImageAcquisitionThread(self)
        self.singleImageAcquisitionThread.start()

    def singleImageAcquired(self, succeeded):
        if succeeded:
            self._display16BitGrayscale(self.singleImageAcquisitionThread.im16g)
        del self.singleImageAcquisitionThread
        self.ui.connectDisconnectAndorDeviceButton.setEnabled(True)
        self.ui.acquireButton.setEnabled(True)
        self.ui.liveStreamBufferCountLabel.setEnabled(True)
        self.ui.liveStreamBufferCountSpinBox.setEnabled(True)
        self.ui.startStopLiveStreamButton.setEnabled(True)

    def startStopLiveStreamButtonClicked(self):
        if not self.isLiveAcquiring:
            # Start live acquisition
            self.ui.connectDisconnectAndorDeviceButton.setEnabled(False)
            self.ui.acquireButton.setEnabled(False)
            self.ui.liveStreamBufferCountLabel.setEnabled(False)
            self.ui.liveStreamBufferCountSpinBox.setEnabled(False)
            self.ui.startStopLiveStreamButton.setText('Stop Live Stream')
            self.liveAcquisitionThread = LiveAcquisitionThread(self, self.ui.liveStreamBufferCountSpinBox.value())
            self.liveAcquisitionThread.start()
            self.isLiveAcquiring = True
        else:
            # Set flag telling the live acquisition thread to exit before it initiates the next AT_WaitBuffer
            self.liveAcquisitionThread.stop = True

    def liveAcquisitionEnded(self):
        del self.liveAcquisitionThread
        self.ui.connectDisconnectAndorDeviceButton.setEnabled(True)
        self.ui.acquireButton.setEnabled(True)
        self.ui.liveStreamBufferCountLabel.setEnabled(False)
        self.ui.liveStreamBufferCountSpinBox.setEnabled(False)
        self.ui.startStopLiveStreamButton.setText('Live Stream')
        self.isLiveAcquiring = False

    def liveImageAcquired(self, bufferIdl):
        bufferId = bufferIdl[0]
        if bufferId != -1:
            buffer = self.liveAcquisitionThread.bufferIdsToBuffers[bufferId]
            self._display16BitGrayscale(buffer[:self.liveAcquisitionThread.aoih, :self.liveAcquisitionThread.aoiw])
            self.liveAcquisitionThread.reQueueBuffer(buffer)

def show(launcherDescription=None, moduleArgs=None):
    import sys
    app = QtWidgets.QApplication(sys.argv)
    mainWindow = AndorManipMainWindow(None)
    mainWindow.show()
    sys.exit(app.exec_())
