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
# Authors: Erik Hvatum <ice.rikh@gmail.com>

import json
from pathlib import Path
from PyQt5 import Qt
import matplotlib.pyplot as plt
import numpy
from skimage import io as skio
for function in ('imread', 'imsave', 'imread_collection'):
    skio.use_plugin('freeimage', function)
import time

class LifeAssayPilot(Qt.QObject):
    def __init__(self, scope, parent=None):
        super().__init__(parent)
        self.scope = scope
        self.dpath = Path('/mnt/scopearray/life_assay_pilot')
        self.name = 'life_assay_pilot'
        self.interval = 1/2 * 60 * 60
        self.video_interval = 4 * 60 * 60
        self.positions_fpath = self.dpath / (self.name + '__positions.json')
        self.checkpoint_fpath = self.dpath / (self.name + '__checkpoint.json')
        self.checkpoint_swaptemp_fpath = self.dpath / (self.name + '__checkpoint.json._')
        self.positions = []
        # indexes of wells to skip
        self.skipped_positions = [5, 7]
        # The index of the most recently completed or currently executing run
        self.run_idx = -1
        # The start time of the most recently completed or currently executing run
        self.run_ts = 0
        # The index of the most recently completed or currently executing video run
        self.video_idx = -1
        # The start time of the most recently completed or currently executing video run
        self.video_ts = 0
        if self.dpath.exists():
            if self.positions_fpath.exists():
                with open(str(self.positions_fpath), 'r') as f:
                    self.positions = json.load(f)
            if self.checkpoint_fpath.exists():
                with open(str(self.checkpoint_fpath), 'r') as f:
                    d = json.load(f)
                self.interval = d['interval']
                self.video_interval = d['video_interval']
                self.run_idx = d['run_idx']
                self.video_idx = d['video_idx']
                self.run_ts = d['run_ts']
                self.video_ts = d['video_ts']
        else:
            self.dpath.mkdir(parents=True)

        self.run_timer = Qt.QTimer(self)
        self.run_timer.timeout.connect(self.execute_run)
        self.run_timer.setSingleShot(True)

    def get_more_positions(self):
        if hasattr(self, 'pos_get_dialog'):
            raise RuntimeError('get_more_positions() already in progress...')
        self.pos_get_dialog = Qt.QDialog()
        self.pos_get_dialog.setAttribute(Qt.Qt.WA_DeleteOnClose, True)
        self.pos_get_dialog.setWindowTitle('Getting positions...')
        self.pos_get_dialog.setLayout(Qt.QVBoxLayout())
        self.pos_get_dialog.store_position_button = Qt.QPushButton('store current position')
        self.pos_get_dialog.layout().addWidget(self.pos_get_dialog.store_position_button)
        self.pos_get_dialog.store_position_button.clicked.connect(self.store_current_position)
        self.pos_get_dialog.plot_positions_button = Qt.QPushButton('plot stored positions')
        self.pos_get_dialog.layout().addWidget(self.pos_get_dialog.plot_positions_button)
        self.pos_get_dialog.plot_positions_button.clicked.connect(self.plot_positions)
        self.pos_get_dialog.stop_button = Qt.QPushButton('stop getting positions')
        self.pos_get_dialog.layout().addWidget(self.pos_get_dialog.stop_button)
        self.pos_get_dialog.stop_button.clicked.connect(self.stop_getting_positions)
        self.pos_get_dialog.show()

    def store_current_position(self):
        self.positions.append(self.scope.stage.position)

    def plot_positions(self):
        if len(self.positions) >= 2:
            positions_npy = numpy.array(self.positions)
            plt.scatter(positions_npy[:,0], -positions_npy[:,1])

    def stop_getting_positions(self):
        self.pos_get_dialog.close()
        del self.pos_get_dialog

    def save_positions(self):
        with open(str(self.positions_fpath), 'w') as f:
            json.dump(self.positions, f)

    def write_checkpoint(self):
        with self.checkpoint_swaptemp_fpath.open('w') as checkpoint_swaptemp_f:
            checkpoint = {'run_idx':self.run_idx,
                          'video_idx':self.video_idx,
                          'run_ts':self.run_ts,
                          'video_ts':self.video_ts,
                          'interval':self.interval,
                          'video_interval':self.video_interval}
            json.dump(checkpoint, checkpoint_swaptemp_f)
        self.checkpoint_swaptemp_fpath.replace(self.checkpoint_fpath)

    def autorun(self):
        if self.interval <= 0:
            raise ValueError('interval must be positive.')
        if self.video_interval <= 0:
            raise ValueError('video_interval must be positive.')
        if self.video_interval < self.interval:
            raise ValueError('interval must be >= video_interval')
        if self.video_interval % self.interval:
            raise ValueError('video_interval must be divisible by interval')
        delta = time.time() - self.run_ts
        if delta >= self.interval:
            self.execute_run()
        else:
            self.run_timer.start((self.interval - delta) * 1000)

    def execute_run(self):
        self.run_ts = time.time()
        self.run_idx += 1
        self.write_checkpoint()
        self.scope.camera.exposure_time = 10
        self.scope.camera.shutter_mode = 'Rolling'
        self.scope.camera.sensor_gain = '16-bit (low noise & high well capacity)'
        for pos_idx, pos in enumerate(self.positions):
            if pos_idx in self.skipped_positions:
                continue
            self.scope.stage.position = pos
            self.scope.tl.lamp.enabled = True
            time.sleep(0.8)
            self.scope.camera.autofocus.autofocus_continuous_move(24.0690702, 25.04415572, 0.2, 'high pass + brenner', max_workers=3)
            im_bf = self.scope.camera.acquire_image()
            self.scope.tl.lamp.enabled = False
            self.scope.il.spectra_x.GreenYellow.intensity = 255
            self.scope.il.spectra_x.GreenYellow.enabled = True
            self.scope.camera.push_state(exposure_time=100)
            time.sleep(0.8)
            im_fluo = self.scope.camera.acquire_image()
            self.scope.il.spectra_x.GreenYellow.enabled = False
            self.scope.camera.pop_state()
            im_dpath = self.dpath / '{:04}'.format(pos_idx)
            if not im_dpath.exists():
                im_dpath.mkdir()
            im_bf_fpath = im_dpath / '{}__{:04}_{:04}_bf.tiff'.format(self.name, pos_idx, self.run_idx)
            skio.imsave(str(im_bf_fpath), im_bf)
            im_fluo_fpath = im_dpath / '{}__{:04}_{:04}_fluo_greenyellow.tiff'.format(self.name, pos_idx, self.run_idx)
            skio.imsave(str(im_fluo_fpath), im_fluo)
        if self.video_interval - (time.time() - self.video_ts) <= 0:
            tps = self.scope.camera.timestamp_ticks_per_second
            self.video_ts = time.time()
            self.video_idx += 1
            self.write_checkpoint()
            for pos_idx, pos in enumerate(self.positions):
                if pos_idx in self.skipped_positions:
                    continue
                ims = []
                self.scope.tl.lamp.enabled = True
                time.sleep(0.8)
                self.scope.stage.position = pos
                self.scope.camera.autofocus.autofocus_continuous_move(24.0690702, 25.04415572, 0.2, 'high pass + brenner', max_workers=3)

                self.scope.camera.reset_timestamp()
                self.scope.camera.start_image_sequence_acquisition(frame_count=300)
                for im_idx in range(300):
                    ims.append((self.scope.camera.next_image(), self.scope.camera.latest_timestamp))
                self.scope.tl.lamp.enabled = False
                self.scope.camera.end_image_sequence_acquisition()
                im_dpath = self.dpath / '{:04}'.format(pos_idx) / 'video_{:04}'.format(self.video_idx)
                if not im_dpath.exists():
                    im_dpath.mkdir()
                for im_idx, im in enumerate(ims):
                    im_fpath = im_dpath / '{}__{:04}_video_{:04}_{:04}_a_{}.tiff'.format(self.name, pos_idx, self.video_idx, im_idx, (im[1] - ims[0][1])/tps)
                    skio.imsave(str(im_fpath), im[0])

                ims = []
                self.scope.tl.lamp.enabled = True
                time.sleep(0.8)
                self.scope.camera.reset_timestamp()
                self.scope.camera.start_image_sequence_acquisition(frame_count=300)
                for im_idx in range(300):
                    ims.append((self.scope.camera.next_image(), self.scope.camera.latest_timestamp))
                self.scope.tl.lamp.enabled = False
                self.scope.camera.end_image_sequence_acquisition()
                im_dpath = self.dpath / '{:04}'.format(pos_idx) / 'video_{:04}'.format(self.video_idx)
                if not im_dpath.exists():
                    im_dpath.mkdir()
                for im_idx, im in enumerate(ims):
                    im_fpath = im_dpath / '{}__{:04}_video_{:04}_{:04}_b_{}.tiff'.format(self.name, pos_idx, self.video_idx, im_idx, (im[1] - ims[0][1])/tps)
                    skio.imsave(str(im_fpath), im[0])
        time_to_next = max(0, self.interval - (time.time() - self.run_ts))
        self.run_timer.start(time_to_next * 1000)
