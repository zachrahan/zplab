#!/usr/bin/env python3

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

import numpy
from pathlib import Path
import skimage.measure
import skimage.morphology
import skimage.io as skio
for function in ('imread', 'imsave', 'imread_collection'):
    skio.use_plugin('freeimage', function)
import multiprocessing
import pickle
import sys

def skeletonizeMask(imageFPath):
    maskFPath = imageFPath.parent / 'fluo_worm_mask.png'
    skeletonFPath = imageFPath.parent / 'fluo_worm_mask_skeleton.png'
    if maskFPath.exists() and not skeletonFPath.exists():
        mask = skio.imread(str(maskFPath)) > 0
        skeleton = skimage.morphology.skeletonize(mask)
        skio.imsave(str(skeletonFPath), skeleton.astype(numpy.uint8)*255)


with open(sys.argv[1], 'rb') as f:
    imageFPaths = pickle.load(f)
with multiprocessing.Pool(5) as pool:
    pool.map(skeletonizeMask, imageFPaths)
