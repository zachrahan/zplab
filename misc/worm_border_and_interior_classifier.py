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

import collections
import math
import numpy
from pathlib import Path
import scipy.ndimage
import scipy.ndimage.morphology
import skimage.exposure
import skimage.measure
import skimage.morphology
import skimage.io as skio
import sklearn.linear_model
import sklearn.neighbors
import sklearn.svm
for function in ('imread', 'imsave', 'imread_collection'):
    skio.use_plugin('freeimage', function)
import multiprocessing
import pickle
import sys

def select_random_coords_in_mask(mask_fpath, coord_count):
    im_mask = skio.imread(str(mask_fpath)) > 0
    labels = skimage.measure.label(im_mask)
    regions = skimage.measure.regionprops(labels)
    if len(regions) == 0:
        raise RuntimeError('No regions found in mask image file "{}".'.format(str(mask_fpath)))

    # Do not select points from voids within mask
    coords = numpy.array([coord for region in regions if im_mask[region.coords[0, 0], region.coords[0, 1]] \
                                for coord in region.coords])

    if coord_count > len(coords):
        print('Warning: coord_count exceeds number of pixels in "{}".  The coordinates of all mask ' + \
              'pixels will be returned without duplication, which is fewer coordinates than requested.')
        coord_count = len(coords)
    if len(coords) == coord_count:
        return coords
    else:
        return coords[numpy.random.choice(range(len(coords)), size=coord_count, replace=False)].astype(numpy.uint32)

def make_patch_feature_vector(imf, patch_width, coord):
    low_edge_offset = int(patch_width / 2)
    # NB: numpy index ranges are open on the right
    high_edge_offset = patch_width - low_edge_offset
    return imf[coord[0]-low_edge_offset : coord[0]+high_edge_offset,
               coord[1]-low_edge_offset : coord[1]+high_edge_offset].ravel()

def make_data_and_targets(im_fpath, mask_set_fpath, patch_width=9, background_sample_count=2000, worm_interior_sample_count=400, worm_wall_sample_count=100):
    mask_set_fpath_str = str(mask_set_fpath)
    imf = skimage.exposure.equalize_adapthist(skio.imread(str(im_fpath))).astype(numpy.float32)
    if imf.max() > 1:
        # For some reason, skimage.exposure.equalize_adapthist rescales to [0, 1] on OS X but not on Linux.
        # [0, 1] scaling is desired.
        imf -= imf.min()
        imf /= imf.max()
    masks = [
        ('_worm_interior.png', worm_interior_sample_count, 1),
        ('_worm_wall.png', worm_wall_sample_count, 2),
        ('_valid_exterior.png', background_sample_count, 0)]
    dats = []
    for mask_fpath_suffix, sample_count, label in masks:
        coords = select_random_coords_in_mask(mask_set_fpath_str + mask_fpath_suffix, sample_count)
        for coord in coords:
            dats.append((make_patch_feature_vector(imf, patch_width, coord), label))
    return dats

def write_libsvm_data_and_targets_file(data_and_targets, libsvm_data_and_targets_fpath):
    '''Note: If file at path lib_svm_data_and_targets_fpath exists, this function will attempt to overwrite it.'''
    with open(str(libsvm_data_and_targets_fpath), 'w') as libsvm_data_and_targets_file:
        for vector, target in data_and_targets:
            l = '{} '.format(target)
            for elementIdx, element in enumerate(vector, 1):
                l += '{}:{} '.format(elementIdx, element)
            l += '\n'
            libsvm_data_and_targets_file.write(l)

def make_libsvm_data_file_for_image(im_fpath, patch_width, libsvm_data_fpath):
    coords = []
    with open(str(libsvm_data_fpath), 'w') as libsvm_data_file:
        imf = skimage.exposure.equalize_adapthist(skio.imread(str(im_fpath))).astype(numpy.float32)
        if imf.max() > 1:
            # For some reason, skimage.exposure.equalize_adapthist rescales to [0, 1] on OS X but not on Linux.
            # [0, 1] scaling is desired.
            imf -= imf.min()
            imf /= imf.max()
        center_offset = patch_width / 2
        ycount = int(imf.shape[0] / patch_width)
        xcount = int(imf.shape[1] / patch_width)
        mask = numpy.zeros((ycount, xcount), dtype=numpy.bool)
        xycount = ycount * xcount
        xyindex = 0
        for yindex in range(ycount):
            y = center_offset + yindex * patch_width
            yi = int(y)
            for xindex in range(xcount):
                x = center_offset + xindex * patch_width
                xi = int(x)
                vector = make_patch_feature_vector(imf, patch_width, (yi, xi))
                if len(vector) > 0:
                    libsvm_data_file.write('-1 ')
                    libsvm_data_file.write(' '.join(('{}:{}'.format(elementIdx, element) for elementIdx, element in enumerate(vector, 1))))
                    libsvm_data_file.write('\n')
                    coords.append((yi, xi))
                xyindex += 1
                print('{}%'.format(100 * xyindex / xycount))
    return coords

def overlay_libsvm_preds_from_file(patch_width, coordList, libSvmPredFPath, imageFPath=None, image=None, maskAlpha=0.3):
    if image is None and imageFPath is None or \
       image is not None and imageFPath is not None:
        raise ValueError('Either the imageFPath or the image argument must be supplied (but not both).')
    if image is None:
        image = skio.imread(imageFPath)

    with open(str(libSvmPredFPath), 'r') as f:
        preds = [bool(int(l[0])) for l in f.readlines()]

    imageCoef = 1 - maskAlpha
    maskVal = maskAlpha * 32767
    rmask = numpy.zeros(image.shape, dtype=numpy.float128)
    low_edge_offset = int(patch_width / 2)
    # NB: numpy index ranges are open on the right
    high_edge_offset = patch_width - low_edge_offset

    for coord, pred in zip(coordList, preds):
        y, x = coord
        if pred > 0:
            rmask[y-low_edge_offset : y+high_edge_offset,
                  x-low_edge_offset : x+high_edge_offset] = maskVal * pred

    composite = rmask + image.astype(numpy.float128) * imageCoef
    return composite.astype(numpy.uint16)
