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

from pathlib import Path
import concurrent.futures as futures
import freeimage
import json
import math
import numpy

def scan_slide(scope, tl, br, increment, dpath, fn_prefix):
    def get_and_store(do_all=False):
        """Get from at least 3 images back so that we don't have to wait
        for the current exposure and read-out until we're ready to finish
        flushing get_stack."""
        if do_all:
            ngets = len(get_stack)
        else:
            if len(get_stack) < 3:
                return
            ngets = 1
        for _ in range(ngets):
            futs.append(threadpool.submit(freeimage.write, scope.camera.next_image(), str(dpath / 'fn_prefix_{}.png'.format(get_stack.pop(0)))))
    z = scope.stage.position[2]
    dpath =  Path(dpath)
    threadpool = futures.ThreadPoolExecutor(3)
    futs = []
    get_stack = []
    x_steps = numpy.linspace(tl[0], br[0], num=math.ceil((br[0]-tl[0])/increment), endpoint=True)
    y_steps = numpy.linspace(tl[1], br[1], num=math.ceil((br[1]-tl[1])/increment), endpoint=True)
    num_steps = len(x_steps) * len(y_steps)
    step_idx = 0
    scope.tl.lamp.push_state(enabled=True)
    scope.camera.start_image_sequence_acquisition(frame_count=num_steps, trigger_mode='Software')
    positions = []
    for x_idx, x in enumerate(x_steps):
        # Scan up if previous scan left us at bottom, scan down if we are at the top or we are doing
        # our first column
        loop_y_steps = reversed(y_steps) if x_idx % 2 == 1 else y_steps
        for y in loop_y_steps: 
            scope.stage.position = [x, y, z]
            scope.camera.send_software_trigger()
            get_stack.append('{:04}'.format(step_idx))
            positions.append((x, y, z))
            get_and_store()
            step_idx += 1
            print('{}/{} ({}%)'.format(step_idx, num_steps, 100 * step_idx/num_steps))
    scope.tl.lamp.pop_state()
    print('Writing remaining images...')
    get_and_store(True)
    with open(str(dpath / '{}_positions.json'.format(fn_prefix)), 'w') as f:
        json.dump(positions, f)
    futures.wait(futs)
    [fut.result() for fut in futs]
