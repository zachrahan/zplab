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
from misc.yapy_liblinear.yapy_liblinear import LinearClassifier
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

class Classifier:
    def __init__(self,
                 liblinear_classifier_object_or_model_fpath,
                 sample_box_width,
                 mask_object_or_fpath=Path(os.path.expanduser('~')) / 'Data' / 'experiment01_a' / 'supplementary_out_exclusion_mask.png',
                 max_accepted_sample_masked_portion=0.25):

        if issubclass(type(liblinear_classifier_object_or_model_fpath), (str, Path)):
            self._linear_classifier = LinearClassifier()
            self._linear_classifier.load(str(liblinear_classifier_object_or_model_fpath))
        else:
            self._linear_classifier = liblinear_classifier_object_or_model_fpath

        self._sample_box_width = sample_box_width
        self._vector_len = self._sample_box_width * self._sample_box_width

        if issubclass(type(mask_object_or_fpath), (str, Path)):
            m = skio.imread(str(mask_object_or_fpath)) > 0
        else:
            m = mask_object_or_fpath > 0
        self._exclusion_mask = skimage.measure.block_reduce(m, (self._sample_box_width, self._sample_box_width), numpy.sum)

        self._max_masked = max_accepted_sample_masked_portion

    def classify(self, im):
        imf = skimage.exposure.equalize_adapthist(im).astype(numpy.float64)
        ybc = int(imf.shape[0] / self._sample_box_width)
        xbc = int(imf.shape[1] / self._sample_box_width)
        mask = numpy.zeros((ybc, xbc), dtype=numpy.bool)
        vectors = numpy.empty((ybc * xbc, self._vector_len), dtype=numpy.float64)
        b = 0
        sbw = self._sample_box_width
        for yb, y in zip(range(ybc), range(0, imf.shape[0], sbw)):
            for xb, x in zip(range(xbc), range(0, imf.shape[1], sbw)):
                vectors[b, :] = imf[y:y+sbw, x:x+sbw].ravel()
                b += 1
        return self._linear_classifier.classify(vectors).reshape(ybc, xbc)

    def classify_and_overlay(self, im, mask_alpha=0.333333):
        mask = self.classify(im) > 0
        mask = numpy.repeat(mask, self._sample_box_width, axis=0)
        mask = numpy.repeat(mask, self._sample_box_width, axis=1)
        mask = numpy.pad(mask, ((0, im.shape[0]-mask.shape[0]), (0, im.shape[1]-mask.shape[1])), 'constant', constant_values=0)
        return (((im.astype(numpy.float32) / im.max()) * (1-mask_alpha) + mask.astype(numpy.float32) * mask_alpha) * 65535).astype(numpy.uint16)

