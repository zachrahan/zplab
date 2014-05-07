# Copyright 2014 WUSTL ZPLAB

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
        im = skio.imread(str(frow[1].fpngpathObj))
        result, focusMeasureName = focusMeasure(im)
        print(result, focusMeasureName)
        results.append(result)
        print(str(frow[1].fpngpathObj) + str(': ') + str(results[-1]))
    if rtable is None:
        rtable = DataFrame({focusMeasureName: results}, index=list(ftable.z_pos))
    else:
        if (list(ftable.z_pos) != rtable.index).any():
            raise AcquisitionException('computeFocusMeasure(ftable, rtable, focusMeasure): ftable and rtable Z positions do not match.')
        rtable[focusMeasureName] = results
    return rtable

class FMs:
    def ss(r):
        return (r**2).sum()

    def sobel_h(im):
        r = FMs.ss(skfilt.hsobel(im))
        return r, "horizontal sobel"

    def bilat_denoise__sobel_h(im):
        r = FMs.ss(skfilt.hsobel(skfilt.denoise_bilateral(im)))
        return r, "bilateral denoise + horizontal sobel"

    def sobel_v(im):
        r = FMs.ss(skfilt.vsobel(im))
        return r, "vertical sobel"

    def bilat_denoise__sobel_v(im):
        r = FMs.ss(skfilt.hsobel(skfilt.denoise_bilateral(im)))
        return r, "bilateral denoise + vertical sobel"

    def canny(im):
        r = FMs.ss(skfilt.canny(im))
        return r, "canny"

    def bottomhat(im):
        r = FMs.ss(skfilt.rank.bottomhat(im, selem=numpy.array([[0,0,1,0,0],[0,1,1,1,0],[1,1,1,1,1],[0,1,1,1,0],[0,0,1,0,0]])))
        return r, "bottomhat"

    def entropy(im):
        r = FMs.ss(skfilt.rank.bottomhat(im, selem=numpy.array([[0,0,1,0,0],[0,1,1,1,0],[1,1,1,1,1],[0,1,1,1,0],[0,0,1,0,0]])))
        return r, "entropy"

    def gaussian_0_5__entropy(im):
        r = FMs.ss(skfilt.rank.bottomhat(skfilt.gaussian_filter(im, 0.5), selem=numpy.array([[0,0,1,0,0],[0,1,1,1,0],[1,1,1,1,1],[0,1,1,1,0],[0,0,1,0,0]])))
        return r, "gaussian_0_5__entropy"

    def gaussian_1__entropy(im):
        r = FMs.ss(skfilt.rank.bottomhat(skfilt.gaussian_filter(im, 1), selem=numpy.array([[0,0,1,0,0],[0,1,1,1,0],[1,1,1,1,1],[0,1,1,1,0],[0,0,1,0,0]])))
        return r, "gaussian_1__entropy"

    def gaussian_2__entropy(im):
        r = FMs.ss(skfilt.rank.bottomhat(skfilt.gaussian_filter(im, 2), selem=numpy.array([[0,0,1,0,0],[0,1,1,1,0],[1,1,1,1,1],[0,1,1,1,0],[0,0,1,0,0]])))
        return r, "gaussian_2__entropy"

    def gaussian_5__entropy(im):
        r = FMs.ss(skfilt.rank.bottomhat(skfilt.gaussian_filter(im, 5), selem=numpy.array([[0,0,1,0,0],[0,1,1,1,0],[1,1,1,1,1],[0,1,1,1,0],[0,0,1,0,0]])))
        return r, "gaussian_5__entropy"

    def all(ftable):
        rtable = None
        for fm in [FMs.sobel_h,
                   FMs.bilat_denoise__sobel_h,
                   FMs.sobel_v,
                   FMs.bilat_denoise__sobel_v,
#                   FMs.canny,
                   FMs.bottomhat,
                   FMs.entropy,
                   FMs.gaussian_0_5__entropy,
                   FMs.gaussian_1__entropy,
                   FMs.gaussian_2__entropy,
                   FMs.gaussian_5__entropy]:
            rtable = computeFocusMeasure(ftable, rtable, fm)
        return rtable

