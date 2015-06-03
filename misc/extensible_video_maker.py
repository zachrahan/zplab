# The MIT License (MIT)
#
# Copyright (c) 2014-2015 WUSTL ZPLAB
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
# Authors: Erik Hvatum <ice.rikh@gmail.com>

import freeimage
from moviepy.video.io.ffmpeg_writer import FFMPEG_VideoWriter
import numpy
from pathlib import Path
from PyQt5 import Qt, uic
import sip

class ControlPane(Qt.QWidget):
    def __init__(self, video_maker):
        super().__init__()
        # Note that uic.loadUiType(..) returns a tuple containing two class types (the form class and the Qt base
        # class).  The line below instantiates the form class.  It is assumed that the .ui file resides in the same
        # directory as this .py file.
        self.ui = uic.loadUiType(str(Path(__file__).parent / 'extensible_video_maker.ui'))[0]()
        self.ui.setupUi(self)
        self.video_maker = video_maker
        video_maker.frame_index_changed.connect(lambda idx: self.ui.frame_index_widget.display(idx))
        self.ui.start_stop_button.clicked.connect(self.on_start_stop)
        video_maker.started_changed.connect(self.on_started_changed)
        self.ui.pause_resume_button.clicked.connect(self.on_pause_resume)
        video_maker.paused_changed.connect(self.on_paused_changed)
        self.ui.write_output_checkbox.toggled.connect(self.on_write_output_toggled)
        video_maker.write_output_changed.connect(self.on_write_output_changed)
        self.ui.status_label.setVisible(False)
        video_maker.operation_completed.connect(self.on_operation_completed)

    def on_operation_completed(self, successful):
        self.ui.status_label.setVisible(True)
        self.ui.status_label.setText('Completed Successfully' if successful else '<font color="red">Failed</font>')

    def on_start_stop(self):
        # Do stuff in response to GUI manipulation
        self.video_maker.started = not self.video_maker.started

    def on_started_changed(self, started):
        # Update GUI in response to property change (which may well have been initiated by a GUI action)
        self.ui.start_stop_button.setText('Stop' if started else 'Start')
        self.ui.pause_resume_button.setEnabled(started)
        self.ui.write_output_checkbox.setEnabled(not started)
        if started:
            self.ui.status_label.setVisible(False)

    def on_pause_resume(self):
        # GUI change
        self.video_maker.paused = not self.video_maker.paused

    def on_paused_changed(self, paused):
        # Property change
        self.ui.pause_resume_button.setText('Resume' if paused else 'Pause')

    def on_write_output_toggled(self, checked):
        # GUI change
        self.video_maker.write_output = checked

    def on_write_output_changed(self, write_output):
        # Property change
        self.ui.write_output_checkbox.setChecked(write_output)

class GV(Qt.QGraphicsView):
    def resizeEvent(self, event):
        self.fitInView(self.scene().sceneRect(), Qt.Qt.KeepAspectRatio)

class ExtensibleVideoMaker(Qt.QMainWindow):
    frame_index_changed = Qt.pyqtSignal(int)
    started_changed = Qt.pyqtSignal(bool)
    paused_changed = Qt.pyqtSignal(bool)
    write_output_changed = Qt.pyqtSignal(bool)
    operation_completed = Qt.pyqtSignal(bool) # Parameter is True if successful, False otherwise
    _advance_frame = Qt.pyqtSignal()

    def __init__(self,
                 video_out_fpath,
                 scale_factor=0.5,
                 video_fps=10,
                 parent=None,
                 ControlPaneClass=ControlPane,
                 GSClass=Qt.QGraphicsScene,
                 GVClass=GV):
        super().__init__(parent)
        self.ffmpeg_writer = None
        self.video_out_fpath = Path(video_out_fpath)
        self.scale_factor = scale_factor
        self.video_fps = video_fps
        self._started = False
        self._paused = False
        self._write_output = True
        self._displayed_frame_idx = -1
        self.setWindowTitle('Video Maker')
        self.gs = GSClass(self)
        self.gs.setBackgroundBrush(Qt.QBrush(Qt.QColor(Qt.Qt.black)))
        self.populate_scene()
        self.gv = GVClass(self.gs)
        self.setCentralWidget(self.gv)
        self.control_pane_dock_widget = Qt.QDockWidget('Control Pane', self)
        self.control_pane_widget = ControlPaneClass(self)
        self.control_pane_dock_widget.setWidget(self.control_pane_widget)
        self.control_pane_dock_widget.setAllowedAreas(Qt.Qt.LeftDockWidgetArea | Qt.Qt.RightDockWidgetArea)
        self.addDockWidget(Qt.Qt.RightDockWidgetArea, self.control_pane_dock_widget)
        # QueuedConnection so that a stop or pause click can sneak in between frames and so that our
        # call stack doesn't grow with the number of sequentially rendered frames
        self._advance_frame.connect(self.on_advance_frame, Qt.Qt.QueuedConnection)

    def __del__(self):
        if self.ffmpeg_writer is not None:
            self.ffmpeg_writer.close()

    @staticmethod
    def normalize_intensity(im):
        imn = im.astype(numpy.float32)
        imn *= 255/im.max()
        imn = imn.astype(numpy.uint8)
        return numpy.dstack((imn, imn, imn))

    @classmethod
    def read_image_file_into_qpixmap_item(cls, im_fpath, qpixmap_item):
        im = cls.normalize_intensity(freeimage.read(str(im_fpath)))
        qim = Qt.QImage(sip.voidptr(im.ctypes.data), im.shape[0], im.shape[1], Qt.QImage.Format_RGB888)
        qpixmap_item.setPixmap(Qt.QPixmap(qim))

    def populate_scene(self):
        raise NotImplementedError()

    def on_start(self):
        if self._write_output:
            if self.video_out_fpath.exists():
                self.video_out_fpath.unlink()
            scene_rect = self.gs.sceneRect()
            desired_size = numpy.array((scene_rect.width(), scene_rect.height()), dtype=int)
            desired_size *= self.scale_factor
            # Odd value width or height causes problems for some codecs
            if desired_size[0] % 2:
                desired_size[0] += 1
            if desired_size[1] % 2:
                desired_size[1] += 1
            self._buffer = numpy.empty((desired_size[1], desired_size[0], 3), dtype=numpy.uint8)
            self._qbuffer = Qt.QImage(sip.voidptr(self._buffer.ctypes.data), desired_size[0], desired_size[1], Qt.QImage.Format_RGB888)
#           self.log_file = open(str(self._dpath / 'video.log'), 'w')
            self.ffmpeg_writer = FFMPEG_VideoWriter(str(self.video_out_fpath), desired_size, fps=self.video_fps, codec='mpeg4', preset='veryslow', bitrate='15000k')#, logfile=self.log_file)
        self._displayed_frame_idx = -1
        self.frame_index_changed.emit(self._displayed_frame_idx)

    def on_stop(self):
        if self._write_output:
            self.ffmpeg_writer.close()
            self.ffmpeg_writer = None

    def on_advance_frame(self):
        if not self._started or self._paused:
            return
        try:
            if not self.update_scene_for_current_frame():
                self.started = False
                self.operation_completed.emit(True)
                return
            self.gs.invalidate()
            if self._write_output:
                self._buffer[:] = 0
                qpainter = Qt.QPainter()
                qpainter.begin(self._qbuffer)
                self.gs.render(qpainter)
                qpainter.end()
                self.ffmpeg_writer.write_frame(self._buffer)
            self._displayed_frame_idx += 1
            self.frame_index_changed.emit(self._displayed_frame_idx)
            self._advance_frame.emit()
        except Exception as e:
            self.started = False
            self.operation_completed.emit(False)
            raise e

    def update_scene_for_current_frame(self):
        # Return True if scene was updated and is prepared to be rendered.
        # Return False if the last frame has already been rendered, the video file should be finalized and closed, and video creation is considered to have completed successfully.
        # Throw an exception if video creation should not or can not continue and should be considered failed.
        raise NotImplementedError()

    @property
    def started(self):
        return self._started

    @started.setter
    def started(self, started):
        if started != self._started:
            if started:
                self.on_start()
                self._started = True
                self.started_changed.emit(started)
                self._advance_frame.emit()
            else:
                self._started = False
                self.started_changed.emit(started)
                self.on_stop()

    @property
    def paused(self):
        return self._paused

    @paused.setter
    def paused(self, paused):
        if paused != self._paused:
            self._paused = paused
            self.paused_changed.emit(self._paused)
            if not paused and self._started:
                self._advance_frame.emit()

    @property
    def write_output(self):
        return self._write_output

    @write_output.setter
    def write_output(self, write_output):
        if write_output != self._write_output:
            if self._started:
                raise ValueError('write_output property can not be modified while started is True.')
            self._write_output = write_output
            self.write_output_changed.emit(write_output)

    @property
    def frame_index(self):
        """Index of last frame rendered since started."""
        return self._displayed_frame_idx
