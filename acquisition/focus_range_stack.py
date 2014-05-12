# Copyright 2014 WUSTL ZPLAB
# Erik Hvatum (ice.rikh@gmail.com)

import matplotlib.pyplot as plt
import numpy
import pandas
from pandas import DataFrame
from pathlib import Path
import re
import skimage.filter as skfilt
import skimage.io as skio

from acquisition.acquisition_exception import AcquisitionException

def acquireFocusRangeStack(mmc, rangeobj, savePath, saveFileNamePrefix):
    '''mmc: An MMCorePy.CMMCore instance.
    rangeobj: A list of Z positions at which to acquire or a generator producing them, such as numpy.arange(0, 11.3, .1)
    or range(0, 10, 2).
    savePath: The path to which output files will be saved; must exist.
    saveFileNamePrefix: The beginning of the filename.  To this, an underscore will be appended, followed by a five digit
    integer, another underscore, the Z position, and finally .npy.'''

    savePathObj = Path(savePath)
    if not savePathObj.exists() or not savePathObj.is_dir():
        raise AcquisitionException('acquireFocusRangeStack(..): Path "{}" does not exist or is not a directory.'.format(savePath))

    for idx, rangeval in enumerate(rangeobj):
        pos = mmc.getPosition('FocusDrive')
        print("Moving from {} to {}.".format(pos, rangeval))
        mmc.setPosition('FocusDrive', rangeval)
        mmc.snapImage()
        image = mmc.getImage()
        saveFN = str(savePathObj / '{}_{:0>5}_{:0>15f}.npy'.format(saveFileNamePrefix, idx, rangeval))
        print('Saving to "{}".'.format(saveFN))
        numpy.save(saveFN, image)

    print("Done!")

def parseFPathObj(fpathObj):
    match = re.search(r'^(.+)_(\d{5})_(.+)\.npy$', str(fpathObj.name))
    if match is not None:
        return {'fpathObj': fpathObj,
                'prefix': match.group(1),
                'index': int(match.group(2)),
                'z_pos': float(match.group(3))};

def lsOrdered(path, prefix):
    pathObj = Path(path)
    if not pathObj.exists() or not pathObj.is_dir():
        raise AcquisitionException('lsOrdered(..): Path "{}" does not exist or is not a directory.'.format(savePath))

    rows = []
    idxs = []
    for fpathObj in pathObj.glob(prefix + '_*.npy'):
        row = parseFPathObj(fpathObj)
        if row is not None:
            idxs.append(row['index'])
            del row['index']
            fpngpathObj = fpathObj.with_suffix('.png')
            if fpngpathObj.exists():
                row['fpngpathObj'] = fpngpathObj
            rows.append(row)

    return DataFrame(rows, idxs).sort_index()

def convertNpysToPngs(path, prefix):
    ftable = lsOrdered(path, prefix)
    for frow in ftable.iterrows():
        outfn = frow[1].fpathObj.with_suffix('.png')
        print('Saving "{}" as "{}".'.format(str(frow[1].fpathObj), str(outfn)))
        skio.imsave(str(outfn), skio.Image(numpy.load(str(frow[1].fpathObj))))

def computeFocusMeasure(ftable, rtable, focusMeasure):
    results = []
    for frow in ftable.iterrows():
        im = numpy.load(str(frow[1].fpathObj)).astype(numpy.float32) / 65535
        result, focusMeasureName = focusMeasure(im)
        print('"{}"("{}"): {}'.format(focusMeasureName, str(frow[1].fpathObj), result))
        results.append(result)
    # Normalize result list for focusMeasure to [0.0, 1.0] so that multiple focus measures can be conveniently plotted with the same Y axis
    results = numpy.array(results, dtype=numpy.float64)
    results -= results.min()
    results /= results.max()
    if rtable is None:
        rtable = DataFrame({focusMeasureName: results}, index=list(ftable.z_pos))
    else:
        if (list(ftable.z_pos) != rtable.index).any():
            raise AcquisitionException('computeFocusMeasure(ftable, rtable, focusMeasure): ftable and rtable Z positions do not match.')
        rtable[focusMeasureName] = results
    return rtable

class FMs:
    structureElement = numpy.array([[0,0,1,0,0],
                                    [0,1,1,1,0],
                                    [1,1,1,1,1],
                                    [0,1,1,1,0],
                                    [0,0,1,0,0]])

    def ss(r):
        return (r.astype(numpy.float64)**2).sum()

    def sobel_h(im):
        try:
            r = FMs.ss(skfilt.hsobel(im))
        except ValueError as e:
            r = numpy.NaN
        return r, "horizontal sobel"

    def sobel_h__bilat_denoise(im):
        try:
            r = FMs.ss(skfilt.hsobel(skfilt.denoise_bilateral(im)))
        except ValueError as e:
            r = numpy.NaN
        return r, "horizontal sobel + bilateral denoise"

    def sobel_v(im):
        try:
            r = FMs.ss(skfilt.vsobel(im))
        except ValueError as e:
            r = numpy.NaN
        return r, "vertical sobel"

    def sobel_v__bilat_denoise(im):
        try:
            r = FMs.ss(skfilt.hsobel(skfilt.denoise_bilateral(im)))
        except ValueError as e:
            r = numpy.NaN
        return r, "vertical sobel + bilateral denoise"

    def canny(im):
        try:
            r = FMs.ss(skfilt.canny(im).astype(int) * 100)
        except ValueError as e:
            r = numpy.NaN
        return r, "canny"

    def bottomhat(im):
        try:
            r = FMs.ss(skfilt.rank.bottomhat(im, FMs.structureElement))
        except ValueError as e:
            r = numpy.NaN
        return r, "bottomhat"

    def bottomhat__gaussian_0_5(im):
        try:
            r = FMs.ss(skfilt.rank.bottomhat(skfilt.gaussian_filter(im, 0.5), FMs.structureElement))
        except ValueError as e:
            r = numpy.NaN
        return r, "bottomhat + gaussian 0.5"

    def bottomhat__gaussian_1(im):
        try:
            r = FMs.ss(skfilt.rank.bottomhat(skfilt.gaussian_filter(im, 1), FMs.structureElement))
        except ValueError as e:
            r = numpy.NaN
        return r, "bottomhat + gaussian 1.0"

    def bottomhat__gaussian_2(im):
        try:
            r = FMs.ss(skfilt.rank.bottomhat(skfilt.gaussian_filter(im, 2), FMs.structureElement))
        except ValueError as e:
            r = numpy.NaN
        return r, "bottomhat + gaussian 2.0"

    def bottomhat__gaussian_5(im):
        try:
            r = FMs.ss(skfilt.rank.bottomhat(skfilt.gaussian_filter(im, 5), FMs.structureElement))
        except ValueError as e:
            r = numpy.NaN
        return r, "bottomhat + gaussian 5.0"

    def tophat(im):
        try:
            r = FMs.ss(skfilt.rank.tophat(im, FMs.structureElement))
        except ValueError as e:
            r = numpy.NaN
        return r, "tophat"

    def tophat__gaussian_0_5(im):
        try:
            r = FMs.ss(skfilt.rank.tophat(skfilt.gaussian_filter(im, 0.5), FMs.structureElement))
        except ValueError as e:
            r = numpy.NaN
        return r, "tophat + gaussian 0.5"

    def tophat__gaussian_1(im):
        try:
            r = FMs.ss(skfilt.rank.tophat(skfilt.gaussian_filter(im, 1), FMs.structureElement))
        except ValueError as e:
            r = numpy.NaN
        return r, "tophat + gaussian 1.0"

    def tophat__gaussian_2(im):
        try:
            r = FMs.ss(skfilt.rank.tophat(skfilt.gaussian_filter(im, 2), FMs.structureElement))
        except ValueError as e:
            r = numpy.NaN
        return r, "tophat + gaussian 2.0"

    def tophat__gaussian_5(im):
        try:
            r = FMs.ss(skfilt.rank.tophat(skfilt.gaussian_filter(im, 5), FMs.structureElement))
        except ValueError as e:
            r = numpy.NaN
        return r, "tophat + gaussian 5.0"

    def entropy(im):
        try:
            r = FMs.ss(skfilt.rank.entropy(im, FMs.structureElement))
        except ValueError as e:
            r = numpy.NaN
        return r, "entropy"

    def entropy__gaussian_0_5(im):
        try:
            r = FMs.ss(skfilt.rank.entropy(skfilt.gaussian_filter(im, 0.5), FMs.structureElement))
        except ValueError as e:
            r = numpy.NaN
        return r, "entropy + gaussian 0.5"

    def entropy__gaussian_1(im):
        try:
            r = FMs.ss(skfilt.rank.entropy(skfilt.gaussian_filter(im, 1), FMs.structureElement))
        except ValueError as e:
            r = numpy.NaN
        return r, "entropy + gaussian 1.0"

    def entropy__gaussian_2(im):
        try:
            r = FMs.ss(skfilt.rank.entropy(skfilt.gaussian_filter(im, 2), FMs.structureElement))
        except ValueError as e:
            r = numpy.NaN
        return r, "entropy + gaussian 2.0"

    def entropy__gaussian_5(im):
        try:
            r = FMs.ss(skfilt.rank.entropy(skfilt.gaussian_filter(im, 5), FMs.structureElement))
        except ValueError as e:
            r = numpy.NaN
        return r, "entropy + gaussian 5.0"

    def tophat__entropy(im):
        try:
            r = FMs.ss(skfilt.rank.tophat(skfilt.rank.entropy(im, FMs.structureElement), FMs.structureElement))
        except ValueError as e:
            r = numpy.NaN
        return r, "tophat + entropy"

    def tophat__entropy__gaussian_0_5(im):
        try:
            r = FMs.ss(skfilt.rank.tophat(skfilt.rank.entropy(skfilt.gaussian_filter(im, 0.5), FMs.structureElement), FMs.structureElement))
        except ValueError as e:
            r = numpy.NaN
        return r, "tophat + entropy + gaussian 0.5"

    def tophat__entropy__gaussian_1(im):
        try:
            r = FMs.ss(skfilt.rank.tophat(skfilt.rank.entropy(skfilt.gaussian_filter(im, 1), FMs.structureElement), FMs.structureElement))
        except ValueError as e:
            r = numpy.NaN
        return r, "tophat + entropy + gaussian 1.0"

    def tophat__entropy__gaussian_2(im):
        try:
            r = FMs.ss(skfilt.rank.tophat(skfilt.rank.entropy(skfilt.gaussian_filter(im, 2), FMs.structureElement), FMs.structureElement))
        except ValueError as e:
            r = numpy.NaN
        return r, "tophat + entropy + gaussian 2.0"

    def tophat__entropy__gaussian_5(im):
        try:
            r = FMs.ss(skfilt.rank.tophat(skfilt.rank.entropy(skfilt.gaussian_filter(im, 5), FMs.structureElement), FMs.structureElement))
        except ValueError as e:
            r = numpy.NaN
        return r, "tophat + entropy + gaussian 5.0"

    def bottomhat__entropy(im):
        try:
            r = FMs.ss(skfilt.rank.bottomhat(skfilt.rank.entropy(im, FMs.structureElement), FMs.structureElement))
        except ValueError as e:
            r = numpy.NaN
        return r, "bottomhat + entropy"

    def bottomhat__entropy__gaussian_0_5(im):
        try:
            r = FMs.ss(skfilt.rank.bottomhat(skfilt.rank.entropy(skfilt.gaussian_filter(im, 0.5), FMs.structureElement), FMs.structureElement))
        except ValueError as e:
            r = numpy.NaN
        return r, "bottomhat + entropy + gaussian 0.5"

    def bottomhat__entropy__gaussian_1(im):
        try:
            r = FMs.ss(skfilt.rank.bottomhat(skfilt.rank.entropy(skfilt.gaussian_filter(im, 1), FMs.structureElement), FMs.structureElement))
        except ValueError as e:
            r = numpy.NaN
        return r, "bottomhat + entropy + gaussian 1.0"

    def bottomhat__entropy__gaussian_2(im):
        try:
            r = FMs.ss(skfilt.rank.bottomhat(skfilt.rank.entropy(skfilt.gaussian_filter(im, 2), FMs.structureElement), FMs.structureElement))
        except ValueError as e:
            r = numpy.NaN
        return r, "bottomhat + entropy + gaussian 2.0"

    def bottomhat__entropy__gaussian_5(im):
        try:
            r = FMs.ss(skfilt.rank.bottomhat(skfilt.rank.entropy(skfilt.gaussian_filter(im, 5), FMs.structureElement), FMs.structureElement))
        except ValueError as e:
            r = numpy.NaN
        return r, "bottomhat + entropy + gaussian 5.0"

    def all(ftable):
        rtable = None
        for fm in [FMs.sobel_h,
                   FMs.sobel_h__bilat_denoise,
                   FMs.sobel_v,
                   FMs.sobel_v__bilat_denoise,
#                  FMs.canny,
                   FMs.bottomhat,
                   FMs.bottomhat__gaussian_0_5,
                   FMs.bottomhat__gaussian_1,
                   FMs.bottomhat__gaussian_2,
                   FMs.bottomhat__gaussian_5,
                   FMs.tophat,
                   FMs.tophat__gaussian_0_5,
                   FMs.tophat__gaussian_1,
                   FMs.tophat__gaussian_2,
                   FMs.tophat__gaussian_5,
                   FMs.entropy,
                   FMs.entropy__gaussian_0_5,
                   FMs.entropy__gaussian_1,
                   FMs.entropy__gaussian_2,
                   FMs.entropy__gaussian_5,
                   FMs.tophat__entropy,
                   FMs.tophat__entropy__gaussian_0_5,
                   FMs.tophat__entropy__gaussian_1,
                   FMs.tophat__entropy__gaussian_2,
                   FMs.tophat__entropy__gaussian_5,
                   FMs.bottomhat__entropy,
                   FMs.bottomhat__entropy__gaussian_0_5,
                   FMs.bottomhat__entropy__gaussian_1,
                   FMs.bottomhat__entropy__gaussian_2,
                   FMs.bottomhat__entropy__gaussian_5]:
            rtable = computeFocusMeasure(ftable, rtable, fm)
        return rtable

    def easyAll(path, prefix):
        ftable = lsOrdered(path, prefix)
        rtable = FMs.all(ftable)
        storePath = Path(path) / (prefix + '.hdf5')
        store = pandas.HDFStore(str(storePath))
        store['rtable'] = rtable
        store['index'] = pandas.Series(ftable.index)
