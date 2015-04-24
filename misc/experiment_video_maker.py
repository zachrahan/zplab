#!/usr/bin/env python

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

import datetime
import freeimage
import json
from moviepy.video.io.ffmpeg_writer import FFMPEG_VideoWriter
import numpy
from pathlib import Path
from PyQt5 import Qt, uic
import sip

class GV(Qt.QGraphicsView):
    def resizeEvent(self, event):
        self.fitInView(self.scene().sceneRect(), Qt.Qt.KeepAspectRatio)

class ExperimentVideoMaker(Qt.QMainWindow):
    OUT_FN = 'video.mkv'
    RENDER_SCALE_DIVISOR = 2
    TITLE_STRING = '{}, set {}, well {:02}, frame {:04}, {}'
    POS_SET_AND_COORDS_SUFFIX = '__position_set_names_and_coords.json'

    frame_index_changed = Qt.pyqtSignal(int)
    started_changed = Qt.pyqtSignal(bool)
    paused_changed = Qt.pyqtSignal(bool)
    write_output_changed = Qt.pyqtSignal(bool)
    operation_completed_successfully = Qt.pyqtSignal()
    _advance_frame = Qt.pyqtSignal()

    def __init__(self, experiment_dpath, image_filename_suffixes, parent=None):
        super().__init__(parent)
        if not experiment_dpath:
            raise ValueError('Please supply the path to the experiment directory as a string or pathlib.Path object.')
        self._ffmpeg_writer = None
        self._dpath = Path(experiment_dpath)
        self._fpath = self._dpath / ExperimentVideoMaker.OUT_FN
        if not self._dpath.exists():
            raise RuntimeError('{} does not exist or is not accessible.'.format(ExperimentVideoMaker.DPATH_STR))
        self._image_filename_suffixes = image_filename_suffixes
        self._started = False
        self._paused = False
        self._write_output = True
        self._position_sets = {}
        self._position_set_names = []
        self._displayed_frame_idx = -1
        self._experiment_name = None
        self.setWindowTitle('Experiment Video Maker')
        self.gs = Qt.QGraphicsScene(self)
        self._populate_scene()
        self.gv = GV(self.gs)
        self.setCentralWidget(self.gv)
        self.control_pane_dock_widget = Qt.QDockWidget('Control Pane', self)
        self.control_pane_widget = ControlPane(self)
        self.control_pane_dock_widget.setWidget(self.control_pane_widget)
        self.control_pane_dock_widget.setAllowedAreas(Qt.Qt.RightDockWidgetArea)
        self.addDockWidget(Qt.Qt.RightDockWidgetArea, self.control_pane_dock_widget)
        # Queued so that a stop or pause click can sneak in between frames and so that our
        # call stack doesn't grow with the number of sequentially rendered frames
        self._advance_frame.connect(self._on_advance_frame, Qt.Qt.QueuedConnection)

    def __del__(self):
        if self._ffmpeg_writer is not None:
            self._ffmpeg_writer.close()

    def _populate_scene(self):
        self.gs.setBackgroundBrush(Qt.QBrush(Qt.Qt.black))
        title_font = Qt.QFont('Courier')
        title_font.setPixelSize(60)
        self.title_item = self.gs.addText(ExperimentVideoMaker.TITLE_STRING.format('', '', 0, 0, '*'*19), title_font)
        self.title_item.setDefaultTextColor(Qt.QColor(Qt.Qt.white))
        self.title_item.moveBy((2560 - self.title_item.boundingRect().width()) / 2, 0)
        self.image_item = self.gs.addPixmap(Qt.QPixmap(2560, 2160))
        self.image_item.moveBy(0, self.title_item.boundingRect().height() + 8)
        self.image_item.setShapeMode(Qt.QGraphicsPixmapItem.BoundingRectShape)
        file_not_found_font = Qt.QFont('Courier')
        file_not_found_font.setPixelSize(300)
        self.file_not_found_item = self.gs.addText('file not found', file_not_found_font)
        self.file_not_found_item.setDefaultTextColor(Qt.QColor(Qt.Qt.red))
        image_item_rect = self.image_item.mapToScene(self.image_item.boundingRect()).boundingRect()
        file_not_found_pos = image_item_rect.center()
        file_not_found_size = self.file_not_found_item.boundingRect().size()
        self.file_not_found_item.setPos(image_item_rect.center())
        self.file_not_found_item.moveBy(-file_not_found_size.width()/2, -file_not_found_size.height()/2)
        self.file_not_found_item.hide()

    def _read_experiment_positions_and_checkpoint(self):
        position_fpaths = list(self._dpath.glob('*{}'.format(ExperimentVideoMaker.POS_SET_AND_COORDS_SUFFIX)))
        if not position_fpaths:
            raise RuntimeError('Failed to find a file ending with {} in {}.'.format(ExperimentVideoMaker.POS_SET_AND_COORDS_SUFFIX, str(self._dpath)))
        if len(position_fpaths) > 1:
            raise RuntimeError('Found multiple files ending with {} in {}.'.format(ExperimentVideoMaker.POS_SET_AND_COORDS_SUFFIX, str(self._dpath)))
        position_fpath = position_fpaths[0]

        self._experiment_name = position_fpath.name[:len(position_fpath.name)-len(ExperimentVideoMaker.POS_SET_AND_COORDS_SUFFIX)]

        checkpoint_fpath = self._dpath / '{}__checkpoint.json'.format(self._experiment_name)
        if not checkpoint_fpath.exists():
            raise RuntimeError('Failed to find experiment checkpoint file "{}".'.format(str(checkpoint_fpath)))

        with position_fpath.open('r') as f:
            self._position_set_names, self._position_sets = json.load(f)
        with checkpoint_fpath.open('r') as f:
            self._last_run_idx = json.load(f)['run_idx']

    def _start(self):
        self._read_experiment_positions_and_checkpoint()
        if self._write_output:
            if self._fpath.exists():
                self._fpath.unlink()
            scene_rect = self.gs.sceneRect()
            desired_size = numpy.array((scene_rect.width(), scene_rect.height()), dtype=int)
            desired_size /= ExperimentVideoMaker.RENDER_SCALE_DIVISOR
            # Odd value width or height causes problems for some codecs
            if desired_size[0] % 2:
                desired_size[0] += 1
            if desired_size[1] % 2:
                desired_size[1] += 1
            self._buffer = numpy.empty((desired_size[1], desired_size[0], 3), dtype=numpy.uint8)
            self._qbuffer = Qt.QImage(sip.voidptr(self._buffer.ctypes.data), desired_size[0], desired_size[1], Qt.QImage.Format_RGB888)
#           self.log_file = open(str(self._dpath / 'video.log'), 'w')
            self._ffmpeg_writer = FFMPEG_VideoWriter(str(self._fpath), desired_size, fps=10, codec='mpeg4', preset='veryslow', bitrate='15000k')#, logfile=self.log_file)
        self._displayed_frame_idx = -1
        def next_frame_generator():
            for pos_set_name in self._position_set_names:
                self._pos_set_name = pos_set_name
                self._pos_set = self._position_sets[self._pos_set_name]
                for well_idx in range(len(self._pos_set)):
                    self._well_idx = well_idx
                    for run_idx in range(self._last_run_idx+1):
                        self._run_idx = run_idx
                        yield
        self._next_frame_generator = next_frame_generator()
        self.frame_index_changed.emit(self._displayed_frame_idx)

    def _stop(self):
        if self._write_output:
            self._ffmpeg_writer.close()
            self._ffmpeg_writer = None

    def _on_advance_frame(self):
        if self._started and not self._paused:
            try:
                next(self._next_frame_generator)
            except StopIteration:
                del self._pos_set_name
                del self._pos_set
                del self._well_idx
                del self._run_idx
                del self._next_frame_generator
                self.started = False
                self.operation_completed_successfully.emit()
                return
            frame_idx = self._displayed_frame_idx + 1
            self._render_frame(frame_idx)
            self._displayed_frame_idx = frame_idx
            self.frame_index_changed.emit(self._displayed_frame_idx)
            if self._write_output:
                self._ffmpeg_writer.write_frame(self._buffer)
            self._advance_frame.emit()

    def _render_frame(self, frame_idx):
        if self._write_output:
            self._buffer[:] = 0
        got_image = False
        for image_filename_suffix in self._image_filename_suffixes:
            im_fpath = self._dpath / '{}_{:04}'.format(self._pos_set_name, self._well_idx) / '{}__{}_{:04}_{:04}_{}.png'.format(self._experiment_name, self._pos_set_name, self._well_idx, self._run_idx, image_filename_suffix)
            if im_fpath.exists():
                ts_str = datetime.datetime.fromtimestamp(im_fpath.stat().st_ctime).isoformat()[:19]
                try:
                    im = ExperimentVideoMaker.normalize_intensity(freeimage.read(str(im_fpath)))
                    qim = Qt.QImage(sip.voidptr(im.ctypes.data), im.shape[0], im.shape[1], Qt.QImage.Format_RGB888)
                    self.file_not_found_item.hide()
                    self.image_item.setPixmap(Qt.QPixmap(qim))
                    self.image_item.show()
                    got_image = True
                    break
                except ValueError:
                    pass
        if not got_image:
            self.file_not_found_item.show()
            self.image_item.hide()
            ts_str = ''
        self.title_item.setPlainText(ExperimentVideoMaker.TITLE_STRING.format(self._experiment_name, self._pos_set_name, self._well_idx, self._run_idx, ts_str))
        self.title_item.setPos((2560 - self.title_item.boundingRect().width()) / 2, 0)
        self.gs.invalidate()
        if self._write_output:
            qpainter = Qt.QPainter()
            qpainter.begin(self._qbuffer)
            self.gs.render(qpainter)
            qpainter.end()

    @property
    def started(self):
        return self._started

    @started.setter
    def started(self, started):
        if started != self._started:
            if started:
                self._start()
                self._started = True
                self.started_changed.emit(started)
                self._advance_frame.emit()
            else:
                self._started = False
                self.started_changed.emit(started)
                self._stop()

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

    @staticmethod
    def normalize_intensity(im):
        imn = im.astype(numpy.float32)
        imn *= 255/im.max()
        imn = imn.astype(numpy.uint8)
        return numpy.dstack((imn, imn, imn))

class ControlPane(Qt.QWidget):
    def __init__(self, lf2vm):
        super().__init__()
        # Note that uic.loadUiType(..) returns a tuple containing two class types (the form class and the Qt base
        # class).  The line below instantiates the form class.  It is assumed that the .ui file resides in the same
        # directory as this .py file.
        self.ui = uic.loadUiType(str(Path(__file__).parent / 'experiment_video_maker.ui'))[0]()
        self.ui.setupUi(self)
        self.lf2vm = lf2vm
        lf2vm.frame_index_changed.connect(lambda idx: self.ui.frame_index_widget.display(idx))
        self.ui.start_stop_button.clicked.connect(self._on_start_stop)
        lf2vm.started_changed.connect(self._on_started_changed)
        self.ui.pause_resume_button.clicked.connect(self._on_pause_resume)
        lf2vm.paused_changed.connect(self._on_paused_changed)
        self.ui.write_output_checkbox.toggled.connect(self._on_write_output_toggled)
        lf2vm.write_output_changed.connect(self._on_write_output_changed)
        self.ui.completed_successfully_label.setVisible(False)
        lf2vm.operation_completed_successfully.connect(lambda: self.ui.completed_successfully_label.setVisible(True))

    def _on_start_stop(self):
        # Do stuff in response to GUI manipulation
        self.lf2vm.started = not self.lf2vm.started

    def _on_started_changed(self, started):
        # Update GUI in response to property change (which may well have been initiated by a GUI action)
        self.ui.start_stop_button.setText('Stop' if started else 'Start')
        self.ui.pause_resume_button.setEnabled(started)
        self.ui.write_output_checkbox.setEnabled(not started)
        self.ui.completed_successfully_label.setVisible(False)

    def _on_pause_resume(self):
        self.lf2vm.paused = not self.lf2vm.paused

    def _on_paused_changed(self, paused):
        self.ui.pause_resume_button.setText('Resume' if paused else 'Pause')

    def _on_write_output_toggled(self, checked):
        self.lf2vm.write_output = checked

    def _on_write_output_changed(self, write_output):
        self.ui.write_output_checkbox.setChecked(write_output)

if __name__ == "__main__":
    import sys
    app = Qt.QApplication(sys.argv)
    if len(sys.argv) < 2:
        raise ValueError('Please supply experiment directory path as the first parameter.')
    if len(sys.argv) < 3:
        raise ValueError('Please supply image filename suffix(es) in descending order of preference as additional parameter(s).')
    vm = ExperimentVideoMaker(sys.argv[1], sys.argv[2:])
    vm.setAttribute(Qt.Qt.WA_DeleteOnClose)
    vm.show()
    app.exec()