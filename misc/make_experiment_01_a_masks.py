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
from misc.image_from_multi_image_statistics import generate_running_percentile_difference
import math
from misc.pca import pca_decompose
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

def generate__bf_bgs_masks__fluo_running_differences__bfs__composites(dpath, bgs_mask_alpha=0.3333, running_difference_alpha=0.3333, percentile=20, run_length=10, crop=None):
    if bgs_mask_alpha > 1 or bgs_mask_alpha < 0 \
       or running_difference_alpha > 1 or running_difference_alpha < 0 \
       or bgs_mask_alpha + running_difference_alpha > 1:
        raise ValueError('bgs_mask_alpha and running_difference_alpha must be in the range [0, 1], as must their sum.')
    dpath = Path(dpath)
    imfpaths = list((dpath / 'bestfmvs').glob('*.PNG'))
    indexes = sorted([int(imfpath.stem) for imfpath in imfpaths])
    fluo_running_percentile_difference_generator = generate_running_percentile_difference(percentile, run_length, crop)
    next(fluo_running_percentile_difference_generator)
    for index in indexes:
        try:
            mask = skio.imread(str(dpath / 'MixtureOfGaussianV2BGS' / '{}.png'.format(index)))
        except ValueError as ve:
            continue
        if (mask == 255).all():
            continue
        fluo = skio.imread(str(dpath / 'fluos' / '{}.PNG'.format(index)))
        if crop:
            mask = mask[:crop[0], :crop[1]]
            fluo = fluo[:crop[0], :crop[1]]
        fluo_difference = fluo_running_percentile_difference_generator.send(fluo)
        if fluo_difference is None:
            yield
            continue
        im = skio.imread(str(dpath / 'bestfmvs' / '{}.PNG'.format(index)))
        if crop:
            im = im[:crop[0], :crop[1]]
        yield ( \
               ( \
                ((im.astype(numpy.float32) - im.min()) / im.max()) * (1 - bgs_mask_alpha - running_difference_alpha) + \
                (mask > 0).astype(numpy.float32) * bgs_mask_alpha + \
                (fluo_difference > 2500).astype(numpy.float32) * running_difference_alpha \
               ) * 65535 \
              ).astype(numpy.uint16)

def fill_voids(mask, max_pixel_count_void_to_fill):
    mask = mask.copy()
    void_labels = skimage.measure.label(~mask)
    void_regions = skimage.measure.regionprops(void_labels)[1:]
    void_regions.sort(key=lambda region: region.area)
    for void_region in void_regions:
        if void_region.area > max_pixel_count_void_to_fill:
            break
        y, x = void_region.coords[0]
        if mask[y, x]:
            # Skip island
            continue
        # Fill void
        mask[void_labels == void_region.label] = True
    return mask

def generate_masks(dpath, percentile=0, run_length=10, d_threshold=3000, max_void_fill=3000, crop=(2160,2560)):
    def make_mask(im):
        mask = im > d_threshold
        mask = scipy.ndimage.binary_dilation(mask, iterations=5)
        mask = fill_voids(mask, max_void_fill)
        return scipy.ndimage.binary_erosion(mask, iterations=4)
    dpath = Path(dpath)
    imfpaths = list((dpath / 'bestfmvs').glob('*.PNG'))
    indexes = sorted([int(imfpath.stem) for imfpath in imfpaths])
    del imfpaths
    bf_rpdg = generate_running_percentile_difference(100 - percentile, run_length)
    fluo_rpdg = generate_running_percentile_difference(percentile, run_length)
    next(bf_rpdg)
    next(fluo_rpdg)
    for index in indexes:
        bf = skio.imread(str(dpath / 'bestfmvs' / '{}.PNG'.format(index)))
        fluo = skio.imread(str(dpath / 'fluos' / '{}.PNG'.format(index)))
        if crop:
            bf = bf[:crop[0], :crop[1]]
            fluo = fluo[:crop[0], :crop[1]]
        bf = bf_rpdg.send(bf)
        fluo = fluo_rpdg.send(fluo)
        if bf is None:
            yield None
            continue
        bf = make_mask(bf)
        fluo = make_mask(fluo)
        yield bf & fluo

def generate__bf_running_differences__fluo_running_differences__bfs__composites(dpath, bf_mask_alpha=0.3333, fluo_mask_alpha=0.3333, percentile=0, run_length=10, crop=None):
    if bf_mask_alpha > 1 or bf_mask_alpha < 0 \
       or fluo_mask_alpha > 1 or fluo_mask_alpha < 0 \
       or bf_mask_alpha + fluo_mask_alpha > 1:
        raise ValueError('bf_mask_alpha and fluo_mask_alpha must be in the range [0, 1], as must their sum.')
    dpath = Path(dpath)
    imfpaths = list((dpath / 'bestfmvs').glob('*.PNG'))
    indexes = sorted([int(imfpath.stem) for imfpath in imfpaths])
    del imfpaths
    bf_rpdg = generate_running_percentile_difference(100 - percentile, run_length)
    fluo_rpdg = generate_running_percentile_difference(percentile, run_length)
    next(bf_rpdg)
    next(fluo_rpdg)
    for index in indexes:
        try:
            bf = skio.imread(str(dpath / 'bestfmvs' / '{}.PNG'.format(index)))
        except ValueError as ve:
            continue
        fluo = skio.imread(str(dpath / 'fluos' / '{}.PNG'.format(index)))
        if crop:
            mask = mask[:crop[0], :crop[1]]
            fluo = fluo[:crop[0], :crop[1]]
        fluo_difference = fluo_rpdg.send(fluo)
        if fluo_difference is None:
            yield
            continue
        im = skio.imread(str(dpath / 'bestfmvs' / '{}.PNG'.format(index)))
        if crop:
            im = im[:crop[0], :crop[1]]
        yield ( \
               ( \
                ((im.astype(numpy.float32) - im.min()) / im.max()) * (1 - bgs_mask_alpha - running_difference_alpha) + \
                (mask > 0).astype(numpy.float32) * bgs_mask_alpha + \
                (fluo_difference > 2500).astype(numpy.float32) * running_difference_alpha \
               ) * 65535 \
              ).astype(numpy.uint16)

def overlay__bf_bgs_masks__bfs__in_flipbook(dpath, rw, mask_alpha):
    dpath = Path(dpath)
    imfpaths = list((dpath / 'bestfmvs').glob('*.PNG'))
    indexes = sorted([int(imfpath.stem) for imfpath in imfpaths])
    cs = []
    for index in indexes:
        try:
            mask = skio.imread(str(dpath / 'MixtureOfGaussianV2BGS' / '{}.png'.format(index)))[:2160,:2560]
        except ValueError as ve:
            continue
        if not (mask == 255).all():
            im = skio.imread(str(dpath / 'bestfmvs' / '{}.PNG'.format(index)))[:2160,:2560]
            cs.append((((im.astype(numpy.float32) / 65535) * (1 - mask_alpha) + (mask > 0).astype(numpy.float32) * mask_alpha)*65535).astype(numpy.uint16))
    rw.showImagesInNewFlipper(cs)

def make_multiclassifier_data_and_targets(im_fpath, mask_set_fpath, patch_width=9, background_sample_count=2000, worm_interior_sample_count=400, worm_wall_sample_count=100,
                                     pca_pcs=None, pca_means=None):
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
    labels = []
    vectors = []
    for mask_fpath_suffix, sample_count, label in masks:
        coords = select_random_coords_in_mask(mask_set_fpath_str + mask_fpath_suffix, sample_count)
        for coord in coords:
            vector = make_patch_feature_vector(imf, patch_width, coord)
            labels.append(label)
            vectors.append(vector)
    if pca_pcs is not None:
        vectors = pca_decompose(vectors, pca_pcs, pca_means)
    else:
        vectors = numpy.array(vectors)
    return vectors, numpy.array(labels)
