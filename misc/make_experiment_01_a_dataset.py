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
import os
import pickle
import sys

supplementary_out_exclusion_mask = skio.imread(str(Path(os.path.expanduser('~')) / 'Data' / 'experiment01_a' / 'supplementary_out_exclusion_mask.png'))

def select_random_in_mask_and_out_mask_coords(mask_fpath, coord_count, separation=None):
    im_mask = skio.imread(str(mask_fpath)) > 0
    labels = skimage.measure.label(im_mask)
    regions = skimage.measure.regionprops(labels)
    if len(regions) == 0:
        raise RuntimeError('No regions found in mask image file "{}".'.format(str(mask_fpath)))

    # Lump together the coordinates of every lit mask pixel
    in_coords = numpy.array([coord for region in regions if im_mask[region.coords[0, 0], region.coords[0, 1]] \
                                   for coord in region.coords])
    print('len(in_coords):', len(in_coords))
    relabel = False

    # Expand masked regions.  In the resulting image, any non-lit pixel is at least separation pixels from
    # the nearest lit pixel in the original mask.
    if separation is not None:
        im_mask = scipy.ndimage.binary_dilation(im_mask, iterations=separation)
        relabel = True

    if supplementary_out_exclusion_mask is not None:
        im_mask |= supplementary_out_exclusion_mask
        relabel = True

    if relabel:
        labels = skimage.measure.label(im_mask)
        regions = skimage.measure.regionprops(labels)

    # Lump together the coordinates of every non-lit mask pixel
    out_coords = numpy.array([coord for region in regions if not im_mask[region.coords[0, 0], region.coords[0, 1]] \
                                    for coord in region.coords])
    print('len(in_coords):', len(out_coords))

    if coord_count > len(in_coords):
        print(('Warning: coord_count exceeds number of lit pixels in "{}".  The coordinates of all mask ' + \
               'pixels will be returned without duplication, which is fewer coordinates than requested.').format(str(mask_fpath)))
        coord_count = len(in_coords)

    if coord_count > len(out_coords):
        print(('Warning: coord_count exceeds number of dark pixels in "{}".  The coordinates of all masked ' + \
               'pixels will be returned without duplication, which is fewer coordinates than requested.').format(str(mask_fpath)))
        coord_count = len(out_coords)

    if len(in_coords) == coord_count:
        selected_in_coords = in_coords
    else:
        selected_in_coords = in_coords[numpy.random.choice(range(len(in_coords)), size=coord_count, replace=False)].astype(numpy.uint32)
    print('len(selected_in_coords):', len(selected_in_coords))
    
    if len(out_coords) == coord_count:
        selected_out_coords = out_coords
    else:
        selected_out_coords = out_coords[numpy.random.choice(range(len(out_coords)), size=coord_count, replace=False)].astype(numpy.uint32)
    print('len(selected_out_coords):', len(selected_out_coords))

    return (numpy.vstack((selected_in_coords, selected_out_coords)),
            numpy.hstack((numpy.ones(coord_count, dtype=numpy.intc), numpy.zeros(coord_count, dtype=numpy.intc))))

def make_patch_feature_vector(imf, patch_width, coord):
    low_edge_offset = int(patch_width / 2)
    # NB: numpy index ranges are open on the right
    high_edge_offset = patch_width - low_edge_offset
    return imf[coord[0]-low_edge_offset : coord[0]+high_edge_offset,
               coord[1]-low_edge_offset : coord[1]+high_edge_offset].ravel()

def make_image_dataset(dpath, image_idx, sample_count, sample_size, sampler=make_patch_feature_vector):
    dpath = Path(dpath)
    coords, targets = select_random_in_mask_and_out_mask_coords(dpath / 'masks' / '{:04}.png'.format(image_idx), sample_count, int(sample_size / 2))
    imf = skimage.exposure.equalize_adapthist(skio.imread(str(dpath / 'bestfmvs' / '{}.PNG'.format(image_idx)))).astype(numpy.float32)
    if imf.max() > 1:
        # For some reason, skimage.exposure.equalize_adapthist rescales to [0, 1] on OS X but not on Linux.
        # [0, 1] scaling is desired.
        imf -= imf.min()
        imf /= imf.max()
    vectors = numpy.array([make_patch_feature_vector(imf, sample_size, coord) for coord in coords])
    return (vectors, targets)

if __name__ == '__main__':
    def _worker_process_function(dpath, sample_count, sample_size):
        mask_dpath = dpath / 'masks'
        mask_fpaths = list(mask_dpath.glob('*.png'))
        idxs = sorted([int(mask_fpath.stem) for mask_fpath in mask_fpaths if mask_fpath.stem.isdigit()])
        vectorss = []
        targetss = []
        for idx in idxs:
            vectors, targets = make_image_dataset(dpath, idx, sample_count, sample_size)
            vectorss.append(vectors)
            targetss.append(targets)
        return (numpy.vstack(vectorss), numpy.hstack(targetss))

    def _process_exception_callback(process_exception):
        print('warning: worker failed with exception:', process_exception)

    import argparse
    argparser = argparse.ArgumentParser(description='Experiment01_a data and target set generator.')
    argparser.add_argument('--wellDevelopmentalSuccessDb',
                           default=Path(os.path.expanduser('~')) / 'Data' / 'experiment01_a' / 'wellDevelopmentalSuccessDb.pickle',
                           type=Path)
    argparser.add_argument('--experiment01-a',
                           default=Path(os.path.expanduser('~')) / 'Data' / 'experiment01_a',
                           type=Path)
    argparser.add_argument('--sample-size', default=51, type=int)
    argparser.add_argument('--sample-count', default=100, type=int)
    argparser.add_argument('--output-file', required=True, type=Path)
    args = argparser.parse_args()
    # Open output file early to avoid doing a lot of processing only to be unable to save the results
    with open(str(args.output_file), 'wb') as output_file:
        with open(str(args.wellDevelopmentalSuccessDb), 'rb') as f:
            well_developmental_success_db = pickle.load(f)
        with multiprocessing.Pool(multiprocessing.cpu_count() + 1) as pool:
            async_results = []
            for p, s in sorted(well_developmental_success_db.items(), key=lambda v: v[0]):
                if s != 'LittleOrNone':
                    async_results.append(pool.apply_async(_worker_process_function,
                                                          (args.experiment01_a / p.parts[-1],
                                                           args.sample_count,
                                                           args.sample_size),
                                                          error_callback=_process_exception_callback))
            pool.close()
            pool.join()
            vectorss = []
            targetss = []
            for async_result in async_results:
                if async_result.successful():
                    vectors, targets = async_result.get()
                    vectorss.append(vectors)
                    targetss.append(targets)
            vectors = numpy.vstack(vectorss)
            targets = numpy.hstack(targetss)
            pickle.dump((vectors, targets), output_file)
