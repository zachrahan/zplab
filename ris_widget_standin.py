#!/usr/bin/env python3

import ctypes as ct
import numpy as np
from OpenGL import GL
import os
from PyQt5 import QtCore, QtGui, QtWidgets, QtOpenGL
import sys
import threading
import time

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

class RisWidgetStandin(QtWidgets.QDialog):
    def __init__(self, parent = None):
        super().__init__(parent)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        self.setWindowTitle('RisWidgetStandin')

        self.graphicsView = QtWidgets.QGraphicsView(self)

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
        self.graphicsView.setViewport(QtOpenGL.QGLWidget(qglf))

        self.graphicsScene = QtWidgets.QGraphicsScene(self)
        self.graphicsScene.setSceneRect(QtCore.QRectF(0, 0, 100, 100))
        self.graphicsView.setScene(self.graphicsScene)
        self.imageItem = None
        self.graphicsView.setDragMode(QtWidgets.QGraphicsView.ScrollHandDrag)

        layout = QtWidgets.QHBoxLayout()
        layout.addWidget(self.graphicsView)
        self.setLayout(layout)

    def _usePixmap(self, pixmap):
        if self.imageItem is None:
            self.imageItem = ImageItem(pixmap)
            self.graphicsScene.addItem(self.imageItem)
        else:
            self.imageItem.updateImage(pixmap)
        self.graphicsScene.setSceneRect(QtCore.QRectF(0, 0, pixmap.width(), pixmap.height()))

    def display16BitGrayscale(self, im16g):
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
