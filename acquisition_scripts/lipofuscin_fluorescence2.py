
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

import json
from pathlib import Path
from PyQt5 import Qt
import matplotlib.pyplot as plt
import numpy
from skimage import io as skio
import freeimage
import time

class LipofuscinFluorescence2(Qt.QObject):
    def __init__(self, scope, parent=None):
        super().__init__(parent)
        self.scope = scope
        self.dpath = Path('/mnt/scopearray/Zhang_William/lipofuscin_fluorescence2')
        self.name = 'lipofuscin_fluorescence2'
        self.interval = 1/2 * 60 * 60
        self.positions_fpath = self.dpath / (self.name + '__positions.json')
        self.checkpoint_fpath = self.dpath / (self.name + '__checkpoint.json')
        self.checkpoint_swaptemp_fpath = self.dpath / (self.name + '__checkpoint.json._')
        self.positions = []
        # indexes of wells to skip
        #self.skipped_positions = [1,2,6,7,12,15,18,20,26,27,29,30,31,33]
        self.skipped_positions = []
        # The index of the most recently completed or currently executing run
        self.run_idx = -1
        # The start time of the most recently completed or currently executing run
        self.run_ts = 0
        if self.dpath.exists():
            if self.positions_fpath.exists():
                with open(str(self.positions_fpath), 'r') as f:
                    self.positions = json.load(f)
            if self.checkpoint_fpath.exists():
                with open(str(self.checkpoint_fpath), 'r') as f:
                    d = json.load(f)
                self.interval = d['interval']
                self.run_idx = d['run_idx']
                self.run_ts = d['run_ts']
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
                          'run_ts':self.run_ts,
                          'interval':self.interval}
            json.dump(checkpoint, checkpoint_swaptemp_f)
        self.checkpoint_swaptemp_fpath.replace(self.checkpoint_fpath)

    def autorun(self):
        if self.interval <= 0:
            raise ValueError('interval must be positive.')
        delta = time.time() - self.run_ts
        if delta >= self.interval:
            self.execute_run()
        else:
            self.run_timer.start((self.interval - delta) * 1000)

    def execute_run(self):
        self.run_ts = time.time()
        self.run_idx += 1
        self.write_checkpoint()
        self.scope.camera.pixel_readout_rate = '280 MHz'
        self.scope.camera.exposure_time = 10
        self.scope.camera.shutter_mode = 'Rolling'
        self.scope.camera.sensor_gain = '16-bit (low noise & high well capacity)'
        self.scope.camera.acquisition_sequencer.new_sequence(GreenYellow=255, Cyan=255, UV=255)
        self.scope.camera.acquisition_sequencer.add_step(exposure_ms=10, tl_enable=True, tl_intensity=78)
        self.scope.camera.acquisition_sequencer.add_step(exposure_ms=10, tl_enable=False, GreenYellow=True)
        self.scope.camera.acquisition_sequencer.add_step(exposure_ms=10, tl_enable=False, Cyan=True)
        self.scope.camera.acquisition_sequencer.add_step(exposure_ms=10, tl_enable=False, UV=True)
        self.scope.camera.acquisition_sequencer.add_step(exposure_ms=10, tl_enable=True, tl_intensity=78)
        for pos_idx, pos in enumerate(self.positions):
            if pos_idx in self.skipped_positions:
                continue
#           tps = self.scope.camera.timestamp_ticks_per_second
            self.scope.stage.position = pos

            self.scope.tl.lamp.intensity=78
            self.scope.tl.lamp.enabled = True
            time.sleep(0.001)
            self.scope.camera.autofocus.hackified_autofocus_continuous_move(pos[2]+-0.5, min(pos[2]+0.5, 25.51), 0.2, max_workers=2)
            self.scope.tl.lamp.enabled = False

            ims = dict(zip( ('bf0','greenyellow','cyan','uv','bf1'), self.scope.camera.acquisition_sequencer.run() ))

            out_dpath = self.dpath / '{:04}'.format(pos_idx)
            if not out_dpath.exists():
                out_dpath.mkdir()
            for name, im in ims.items():
                im_fpath = out_dpath / '{}__{:04}_{:04}_{}_autofocus.png'.format(self.name, pos_idx, self.run_idx, name)
                freeimage.write(im, str(im_fpath), flags=freeimage.IO_FLAGS.PNG_Z_BEST_SPEED)


            self.scope.stage.position = pos
            ims = dict(zip( ('bf0','greenyellow','cyan','uv','bf1'), self.scope.camera.acquisition_sequencer.run() ))

            out_dpath = self.dpath / '{:04}'.format(pos_idx)
            if not out_dpath.exists():
                out_dpath.mkdir()
            for name, im in ims.items():
                im_fpath = out_dpath / '{}__{:04}_{:04}_{}.png'.format(self.name, pos_idx, self.run_idx, name)
                freeimage.write(im, str(im_fpath), flags=freeimage.IO_FLAGS.PNG_Z_BEST_SPEED)

#           meta_fpath = out_dpath / '{}__{:04}_{:04}.json'.format(self.name, pos_idx, self.run_idx)
#           with meta_fpath.open('w') as f:
#               json.dump({'sequence_timestamps' : times}, f)

        time_to_next = max(0, self.interval - (time.time() - self.run_ts))
        self.run_timer.start(time_to_next * 1000)

    def make_focus_stacks(self):
        self.scope.camera.pixel_readout_rate = '280 MHz'
        self.scope.camera.exposure_time = 10
        self.scope.camera.shutter_mode = 'Rolling'
        self.scope.camera.sensor_gain = '16-bit (low noise & high well capacity)'

        for pos_idx, pos in enumerate(self.positions):
            if pos_idx in self.skipped_positions:
                continue
            self.scope.stage.position = pos

            ims = []
            self.scope.tl.lamp.intensity=88
            self.scope.tl.lamp.enabled = True
            self.scope.camera.binning = '1x1'
            time.sleep(0.001)
            self.scope.camera.start_image_sequence_acquisition(frame_count=100, trigger_mode='Software')
            for z in numpy.linspace(pos[2]-0.5, min(pos[2]+0.5, 25.51), 100, endpoint=True):
                z = float(z)
                self.scope.stage.z = z
                self.scope.camera.send_software_trigger()
                ims.append((self.scope.camera.next_image(), z))
            self.scope.tl.lamp.enabled = False
            self.scope.camera.end_image_sequence_acquisition()

            out_dpath = self.dpath / '{:04}'.format(pos_idx) / 'z_stack'
            if not out_dpath.exists():
                out_dpath.mkdir()
            for idx, (im, z) in enumerate(ims):
                im_fpath = out_dpath / '{}__{:04}_{:04}_{}_1x1.png'.format(self.name, pos_idx, idx, z)
                freeimage.write(im, str(im_fpath), flags=freeimage.IO_FLAGS.PNG_Z_BEST_SPEED)

            ims = []
            self.scope.tl.lamp.intensity=51
            self.scope.tl.lamp.enabled = True
            self.scope.camera.binning = '2x2'
            time.sleep(0.001)
            self.scope.camera.start_image_sequence_acquisition(frame_count=100, trigger_mode='Software')
            for z in numpy.linspace(pos[2]-0.5, min(pos[2]+0.5, 25.51), 100, endpoint=True):
                z = float(z)
                self.scope.stage.z = z
                self.scope.camera.send_software_trigger()
                ims.append((self.scope.camera.next_image(), z))
            self.scope.tl.lamp.enabled = False
            self.scope.camera.end_image_sequence_acquisition()

            out_dpath = self.dpath / '{:04}'.format(pos_idx) / 'z_stack'
            if not out_dpath.exists():
                out_dpath.mkdir()
            for idx, (im, z) in enumerate(ims):
                im_fpath = out_dpath / '{}__{:04}_{:04}_{}_2x2.png'.format(self.name, pos_idx, idx, z)
                freeimage.write(im, str(im_fpath), flags=freeimage.IO_FLAGS.PNG_Z_BEST_SPEED)

            ims = []
            self.scope.tl.lamp.intensity=43
            self.scope.tl.lamp.enabled = True
            self.scope.camera.binning = '3x3'
            time.sleep(0.001)
            self.scope.camera.start_image_sequence_acquisition(frame_count=100, trigger_mode='Software')
            for z in numpy.linspace(pos[2]-0.5, min(pos[2]+0.5, 25.51), 100, endpoint=True):
                z = float(z)
                self.scope.stage.z = z
                self.scope.camera.send_software_trigger()
                ims.append((self.scope.camera.next_image(), z))
            self.scope.tl.lamp.enabled = False
            self.scope.camera.end_image_sequence_acquisition()

            out_dpath = self.dpath / '{:04}'.format(pos_idx) / 'z_stack'
            if not out_dpath.exists():
                out_dpath.mkdir()
            for idx, (im, z) in enumerate(ims):
                im_fpath = out_dpath / '{}__{:04}_{:04}_{}_3x3.png'.format(self.name, pos_idx, idx, z)
                freeimage.write(im, str(im_fpath), flags=freeimage.IO_FLAGS.PNG_Z_BEST_SPEED)

            ims = []
            self.scope.tl.lamp.intensity=41
            self.scope.tl.lamp.enabled = True
            self.scope.camera.binning = '4x4'
            time.sleep(0.001)
            self.scope.camera.start_image_sequence_acquisition(frame_count=100, trigger_mode='Software')
            for z in numpy.linspace(pos[2]-0.5, min(pos[2]+0.5, 25.51), 100, endpoint=True):
                z = float(z)
                self.scope.stage.z = z
                self.scope.camera.send_software_trigger()
                ims.append((self.scope.camera.next_image(), z))
            self.scope.tl.lamp.enabled = False
            self.scope.camera.end_image_sequence_acquisition()

            for idx, (im, z) in enumerate(ims):
                im_fpath = out_dpath / '{}__{:04}_{:04}_{}_4x4.png'.format(self.name, pos_idx, idx, z)
                freeimage.write(im, str(im_fpath), flags=freeimage.IO_FLAGS.PNG_Z_BEST_SPEED)
