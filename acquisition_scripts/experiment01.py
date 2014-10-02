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
# Authors: Erik Hvatum 
 
import json
import pickle
from PyQt5 import Qt
from pathlib import Path
from skimage import io as skio
for function in ('imread', 'imsave', 'imread_collection'):
    skio.use_plugin('freeimage', function)
import time

from acquisition_scripts.autofocus import LinearSearchAutofocuser

def coroutine(func):
    def start(*args,**kwargs):
        cr = func(*args,**kwargs)
        next(cr)
        return cr
    return start

class Experiment01(Qt.QObject):
    _execute_run_completed = Qt.pyqtSignal()

    def __init__(self, root, out_dir, prefix, z_min, z_max, rw = None):
        super().__init__()
        self.root = root
        self.positions = []
        self.out_dir = Path(out_dir)
        self.prefix = prefix
        if not self.out_dir.exists():
            self.out_dir.mkdir(parents=True)
        self.positions_fpath = self.out_dir / (self.prefix + '__positions.pickle')
        with open(str(self.positions_fpath), 'rb') as f:
            self.positions = pickle.load(f)
        self.checkpoint_fpath = self.out_dir / '{}__checkpoint.json'.format(self.prefix)
        self.checkpoint_swaptemp_fpath = self.out_dir / '{}__checkpoint.json._'.format(self.prefix)

        # The index of the most recently completed or currently executing run
        self.run_idx = -1
        # The start time of the most recently completed or currently executing run
        self.run_ts = 0
        if self.checkpoint_fpath.exists():
            with self.checkpoint_fpath.open() as checkpoint_f:
                checkpoint = json.load(checkpoint_f)
            self.interval = checkpoint['interval']
            self.run_idx = checkpoint['run_idx']
            self.run_ts = checkpoint['run_ts']

        self.run_timer = Qt.QTimer(self)
        self.run_timer.timeout.connect(self._launch_execute_run)
        self.run_timer.setSingleShot(True)

        self.autofocuser = LinearSearchAutofocuser(root.camera, root.dm6000b.stageZ, z_min, z_max, 10, 3, rw=rw)

        self._execute_run_gen = None
        self._execute_run_completed.connect(self._execute_run_completed_slot, Qt.Qt.QueuedConnection)

    def _write_checkpoint(self):
        with self.checkpoint_swaptemp_fpath.open('w') as checkpoint_swaptemp_f:
            checkpoint = {'run_idx':self.run_idx,
                          'run_ts':self.run_ts,
                          'interval':self.interval}
            json.dump(checkpoint, checkpoint_swaptemp_f)
        self.checkpoint_swaptemp_fpath.replace(self.checkpoint_fpath)

    def start(self, interval):
        if self.checkpoint_fpath.exists():
            raise RuntimeError('Either use resume() or delete "{}" (the checkpoint file) before calling start(..).'.format(str(self.checkpoint_fpath)))
        self.interval = interval
        self.run_idx = -1
        self.run_ts = 0
        self._write_checkpoint()
        self.resume()

    def resume(self):
        if self.interval <= 0:
            raise ValueError('interval must be positive.')
        delta = time.time() - self.run_ts
        if delta >= self.interval:
            self._launch_execute_run()
        else:
            self.run_timer.start((self.interval - delta) * 1000)

    def _auto_focus_done_slot(self, was_successful):
        try:
            self._execute_run_gen.send(was_successful)
        except StopIteration:
            pass

    def _launch_execute_run(self):
        if self._execute_run_gen is not None:
            raise RuntimeError('Experiment01 is already running.')
        self.autofocuser.autoFocusDone.connect(self._auto_focus_done_slot)
        self._execute_run_gen = self._execute_run()

    def _execute_run_completed_slot(self):
        self._execute_run_gen = None
        self.autofocuser.autoFocusDone.disconnect(self._auto_focus_done_slot)

    @coroutine
    def _execute_run(self):
        self.run_ts = time.time()
        self.run_idx += 1
        self._write_checkpoint()
        self.root.brightfieldLed.enabled = True
        # Paranoia: ensure that brightfield LED has had time to reach full intensity
        time.sleep(0.08)
        for pos_idx, pos in enumerate(self.positions):
            self.root.dm6000b.stageX.pos = pos[0]
            self.root.dm6000b.stageY.pos = pos[1]
            self.root.dm6000b.waitForReady()
            self.autofocuser.start()
            autofocus_successfull = yield
            if not autofocus_successfull or self.autofocuser.bestZ is None:
                print('warning: autofocus failed, skipping position {} for run {}.'.format(pos_idx, self.run_idx))
                continue
            self.root.dm6000b.stageZ.pos = self.autofocuser.bestZ
            self.root.dm6000b.waitForReady()
            self.root.camera._camera.AT_Flush()
            im = self.root.camera.makeAcquisitionBuffer()
            self.root.camera._camera.AT_QueueBuffer(im)
            self.root.camera._camera.AT_Command(self.root.camera._camera.Feature.AcquisitionStart)
            self.root.camera.commandSoftwareTrigger()
            self.root.camera._camera.AT_WaitBuffer(1000)
            self.root.camera._camera.AT_Command(self.root.camera._camera.Feature.AcquisitionStop)
            im_fpath = self.out_dir / '{:04}'.format(pos_idx)
            if not im_fpath.exists():
                im_fpath.mkdir()
            im_fpath /= '{}__{:04}_{:04}.png'.format(self.prefix, pos_idx, self.run_idx)
            skio.imsave(str(im_fpath), im)
        self.root.brightfieldLed.enabled = False
        self._execute_run_completed.emit()
        time_to_next = max(0, self.interval - (time.time() - self.run_ts))
        self.run_timer.start(time_to_next * 1000)
