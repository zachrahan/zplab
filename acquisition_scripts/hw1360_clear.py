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

from scope.timecourse import timecourse_handler
import sys
import pathlib
import numpy
import time

class HW1360Clear(timecourse_handler.TimepointHandler):
    def __init__(self):
        super().__init__(data_dir='/mnt/scopearray/Earley_Brian/hw1360_clear')

    def configure_timepoint(self):
        self.scope.il.shutter_open = True
        self.scope.tl.shutter_open = True
        self.scope.nosepiece.magnification = 10
        self.scope.camera.pixel_readout_rate = '280 MHz'
        self.scope.camera.shutter_mode = 'Rolling'
        self.scope.camera.sensor_gain = '16-bit (low noise & high well capacity)'

    def autofocus(self):
        pos = self.scope.stage.position
        self.scope.tl.lamp.intensity = 69
        self.scope.tl.lamp.enabled = True
        self.scope.camera.exposure_time = 10
        # More binning gives higher contrast, meaning less light needed
        self.scope.camera.binning = '4x4'
        time.sleep(0.001)
        self.scope.camera.autofocus.new_autofocus_continuous_move(pos[2]-0.5, min(pos[2]+0.5, 24.311678), 0.2, metric='high pass + brenner', max_workers=2)
        coarse_z = self.scope.stage.z
        self.scope.camera.binning = '1x1'
        self.scope.tl.lamp.intensity = 117
        time.sleep(0.001)
        self.scope.camera.autofocus.new_autofocus_continuous_move(coarse_z-0.15, min(coarse_z+0.15, 24.311678), 0.1, metric='high pass + brenner', max_workers=2)
        self.scope.tl.lamp.enabled = False
        fine_z = self.scope.stage.z
        return coarse_z, fine_z

    def acquire_images(self, position_name, position_dir, timepoint_prefix, previous_timepoints, previous_metadata):
        coarse_z, fine_z = self.autofocus()

        self.scope.camera.acquisition_sequencer.new_sequence(cyan=255)
        self.scope.camera.acquisition_sequencer.add_step(exposure_ms=10, tl_enable=True, tl_intensity=117)
        self.scope.camera.acquisition_sequencer.add_step(exposure_ms=200, tl_enable=False, cyan=True)

        im_names = ['bf.png', 'gfp.png']
        ims = self.scope.camera.acquisition_sequencer.run()
        self.logger.info('num images {} type', len(ims))
        im_tses = self.scope.camera.acquisition_sequencer.latest_timestamps

        ts_hz = self.scope.camera.timestamp_hz
        t0 = im_tses[0]
        metadata = {
            'coarse_z' : coarse_z,
            'fine_z' : fine_z,
            'image_camera_timestamp_deltas' : list(zip(im_names, [(im_ts - t0)/ts_hz for im_ts in im_tses]))
        }

        return ims, im_names, metadata

handler = HW1360Clear()
timecourse_handler.main(timepoint_function=handler.run_timepoint, next_run_interval=30*60, interval_mode='scheduled_start')
