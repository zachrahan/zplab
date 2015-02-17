import numpy
from pathlib import Path
import freeimage
import time

X_RANGE = 15.89537109375
Y_RANGE = 50.92685546875

def make_references(scope, dpath, prefix):
    '''Position stage at min x and y coordinates of slide before calling this function.'''
    dpath = Path(dpath)
    start_pos = scope.stage.position
    idx = 0
    ims = []
    for x in numpy.linspace(start_pos[0], start_pos[0]+X_RANGE, 2, True):
        for y in numpy.linspace(start_pos[1], start_pos[1]+Y_RANGE, 15, True):
            try:
                scope.stage.position = (x, y, start_pos[2])
            except:
                pass
            time.sleep(0.1)
            im = scope.camera.acquire_image()
            freeimage.write(im, str(dpath / '{}_{:02}.png'.format(prefix, idx)), flags=freeimage.IO_FLAGS.PNG_Z_BEST_SPEED)
            idx += 1
            ims.append(im)
    im = numpy.median(ims, axis=0).astype(numpy.uint16)
    freeimage.write(im, str(dpath / '{}_MEDIAN.png'.format(prefix)), flags=freeimage.IO_FLAGS.PNG_Z_BEST_SPEED)
    scope.position = start_pos
