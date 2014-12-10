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

import time

class StageMovementDataCollector:
    def __init__(self, stage, axis):
        self.stage = stage
        self.axis = axis
        get = 'get_{}'.format(self.axis)
        set = 'set_{}'.format(self.axis)
        self._get_pos = getattr(self.stage, get)
        self._set_pos = getattr(self.stage, set)
        self._get_speed = getattr(self.stage, get + '_speed')
        self._set_speed = getattr(self.stage, set + '_speed')
        self.speed_range = getattr(self.stage, get + '_speed_range')()
        self.runs = []

    def run(self, speed, approx_time):
        if speed < self.speed_range[0] or speed > self.speed_range[1]:
            raise ValueError('speed for axis {} must be in the range [{}, {}].'.format(self.axis, self.speed_range[0], self.speed_range[1]))
        if approx_time <= 0:
            raise ValueError('approx_time must be > 0.')
        was_async = self.stage.get_async()
        self.stage.set_async(False)
        self._set_speed(self.speed_range[1] - 1)
        self._set_pos(0)
        self._set_speed(speed)
        run = [(0, 0)]
        t0 = time.time()
        self.stage.set_async(True)
        self._set_pos(approx_time * speed * 0.1455)
        while self.stage.has_pending():
            run.append((time.time() - t0, self._get_pos()))
        self.runs.append((speed, run))
        self.stage.set_async(was_async)
