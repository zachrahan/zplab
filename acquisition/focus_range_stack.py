# Copyright 2014 WUSTL ZPLAB
# Erik Hvatum (ice.rikh@gmail.com)

if __name__ == "__main__":
    import sys
    sys.path.insert(0, '/home/ehvatum/zplrepo')
    import skimage.io as skio
    for function in ('imread', 'imsave', 'imread_collection'):
        skio.use_plugin('freeimage', function)

import matplotlib.pyplot as plt
from multiprocessing import Process, Pipe, Lock
from scipy.ndimage import filters as ndfilt
import numpy
import pandas
from pandas import DataFrame
from pathlib import Path
import pickle
import re
import skimage.filter as skif
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

def brenner(im, direction):
    if direction == 'h':
        xo = 2
        yo = 0
    elif direction == 'v':
        xo = 0
        yo = 2
    else:
        raise ValueError('direction must be h or v.')
    iml = numpy.pad(im[0:im.shape[0]-yo, 0:im.shape[1]-xo], ((yo, 0), (xo, 0)), mode='constant')
    imr = im.copy()
    if direction == 'h':
        imr[:, :xo] = 0
    else:
        imr[:yo, :] = 0
    return iml - imr

def brennervh(im):
    imh = brenner(im, 'h')
    imv = brenner(im, 'v')
    return numpy.sqrt(imh**2 + imv**2)

class FMs:
    structureElement = numpy.array([[0,0,1,0,0],
                                    [0,1,1,1,0],
                                    [1,1,1,1,1],
                                    [0,1,1,1,0],
                                    [0,0,1,0,0]])

    def ss(r, mask):
        r = r.astype(numpy.float64)
        if mask is not None:
            r = numpy.ma.array(r, mask=mask)
        return (r**2).sum()

    def sobel_h(im, mask=None):
        try:
            r = FMs.ss(skif.hsobel(im), mask)
        except ValueError as e:
            r = numpy.NaN
        return r, "horizontal sobel"

    def sobel_h__bilat_denoise(im, mask=None):
        try:
            r = FMs.ss(skif.hsobel(skif.denoise_bilateral(im)), mask)
        except ValueError as e:
            r = numpy.NaN
        return r, "horizontal sobel + bilateral denoise"

    def sobel_v(im, mask=None):
        try:
            r = FMs.ss(skif.vsobel(im), mask)
        except ValueError as e:
            r = numpy.NaN
        return r, "vertical sobel"

    def sobel_v__bilat_denoise(im, mask=None):
        try:
            r = FMs.ss(skif.hsobel(skif.denoise_bilateral(im)), mask)
        except ValueError as e:
            r = numpy.NaN
        return r, "vertical sobel + bilateral denoise"

    def canny(im, mask=None):
        try:
            r = FMs.ss(skif.canny(im).astype(int) * 100)
        except ValueError as e:
            r = numpy.NaN
        return r, "canny"

    def bottomhat(im, mask=None):
        try:
            r = FMs.ss(skif.rank.bottomhat(im, FMs.structureElement), mask)
        except ValueError as e:
            r = numpy.NaN
        return r, "bottomhat"

    def bottomhat__gaussian_0_5(im, mask=None):
        try:
            r = FMs.ss(skif.rank.bottomhat(skif.gaussian_filter(im, 0.5), FMs.structureElement), mask)
        except ValueError as e:
            r = numpy.NaN
        return r, "bottomhat + gaussian 0.5"

    def bottomhat__gaussian_1(im, mask=None):
        try:
            r = FMs.ss(skif.rank.bottomhat(skif.gaussian_filter(im, 1), FMs.structureElement), mask)
        except ValueError as e:
            r = numpy.NaN
        return r, "bottomhat + gaussian 1.0"

    def bottomhat__gaussian_2(im, mask=None):
        try:
            r = FMs.ss(skif.rank.bottomhat(skif.gaussian_filter(im, 2), FMs.structureElement), mask)
        except ValueError as e:
            r = numpy.NaN
        return r, "bottomhat + gaussian 2.0"

    def bottomhat__gaussian_5(im, mask=None):
        try:
            r = FMs.ss(skif.rank.bottomhat(skif.gaussian_filter(im, 5), FMs.structureElement), mask)
        except ValueError as e:
            r = numpy.NaN
        return r, "bottomhat + gaussian 5.0"

    def tophat(im, mask=None):
        try:
            r = FMs.ss(skif.rank.tophat(im, FMs.structureElement), mask)
        except ValueError as e:
            r = numpy.NaN
        return r, "tophat"

    def tophat__gaussian_0_5(im, mask=None):
        try:
            r = FMs.ss(skif.rank.tophat(skif.gaussian_filter(im, 0.5), FMs.structureElement), mask)
        except ValueError as e:
            r = numpy.NaN
        return r, "tophat + gaussian 0.5"

    def tophat__gaussian_1(im, mask=None):
        try:
            r = FMs.ss(skif.rank.tophat(skif.gaussian_filter(im, 1), FMs.structureElement), mask)
        except ValueError as e:
            r = numpy.NaN
        return r, "tophat + gaussian 1.0"

    def tophat__gaussian_2(im, mask=None):
        try:
            r = FMs.ss(skif.rank.tophat(skif.gaussian_filter(im, 2), FMs.structureElement), mask)
        except ValueError as e:
            r = numpy.NaN
        return r, "tophat + gaussian 2.0"

    def tophat__gaussian_5(im, mask=None):
        try:
            r = FMs.ss(skif.rank.tophat(skif.gaussian_filter(im, 5), FMs.structureElement), mask)
        except ValueError as e:
            r = numpy.NaN
        return r, "tophat + gaussian 5.0"

    def entropy(im, mask=None):
        try:
            r = FMs.ss(skif.rank.entropy(im, FMs.structureElement), mask)
        except ValueError as e:
            r = numpy.NaN
        return r, "entropy"

    def entropy__gaussian_0_5(im, mask=None):
        try:
            r = FMs.ss(skif.rank.entropy(skif.gaussian_filter(im, 0.5), FMs.structureElement), mask)
        except ValueError as e:
            r = numpy.NaN
        return r, "entropy + gaussian 0.5"

    def entropy__gaussian_1(im, mask=None):
        try:
            r = FMs.ss(skif.rank.entropy(skif.gaussian_filter(im, 1), FMs.structureElement), mask)
        except ValueError as e:
            r = numpy.NaN
        return r, "entropy + gaussian 1.0"

    def entropy__gaussian_2(im, mask=None):
        try:
            r = FMs.ss(skif.rank.entropy(skif.gaussian_filter(im, 2), FMs.structureElement), mask)
        except ValueError as e:
            r = numpy.NaN
        return r, "entropy + gaussian 2.0"

    def entropy__gaussian_5(im, mask=None):
        try:
            r = FMs.ss(skif.rank.entropy(skif.gaussian_filter(im, 5), FMs.structureElement), mask)
        except ValueError as e:
            r = numpy.NaN
        return r, "entropy + gaussian 5.0"

    def tophat__entropy(im, mask=None):
        try:
            r = FMs.ss(skif.rank.tophat(skif.rank.entropy(im, FMs.structureElement), FMs.structureElement), mask)
        except ValueError as e:
            r = numpy.NaN
        return r, "tophat + entropy"

    def tophat__entropy__gaussian_0_5(im, mask=None):
        try:
            r = FMs.ss(skif.rank.tophat(skif.rank.entropy(skif.gaussian_filter(im, 0.5), FMs.structureElement), FMs.structureElement), mask)
        except ValueError as e:
            r = numpy.NaN
        return r, "tophat + entropy + gaussian 0.5"

    def tophat__entropy__gaussian_1(im, mask=None):
        try:
            r = FMs.ss(skif.rank.tophat(skif.rank.entropy(skif.gaussian_filter(im, 1), FMs.structureElement), FMs.structureElement), mask)
        except ValueError as e:
            r = numpy.NaN
        return r, "tophat + entropy + gaussian 1.0"

    def tophat__entropy__gaussian_2(im, mask=None):
        try:
            r = FMs.ss(skif.rank.tophat(skif.rank.entropy(skif.gaussian_filter(im, 2), FMs.structureElement), FMs.structureElement), mask)
        except ValueError as e:
            r = numpy.NaN
        return r, "tophat + entropy + gaussian 2.0"

    def tophat__entropy__gaussian_5(im, mask=None):
        try:
            r = FMs.ss(skif.rank.tophat(skif.rank.entropy(skif.gaussian_filter(im, 5), FMs.structureElement), FMs.structureElement), mask)
        except ValueError as e:
            r = numpy.NaN
        return r, "tophat + entropy + gaussian 5.0"

    def bottomhat__entropy(im, mask=None):
        try:
            r = FMs.ss(skif.rank.bottomhat(skif.rank.entropy(im, FMs.structureElement), FMs.structureElement), mask)
        except ValueError as e:
            r = numpy.NaN
        return r, "bottomhat + entropy"

    def bottomhat__entropy__gaussian_0_5(im, mask=None):
        try:
            r = FMs.ss(skif.rank.bottomhat(skif.rank.entropy(skif.gaussian_filter(im, 0.5), FMs.structureElement), FMs.structureElement), mask)
        except ValueError as e:
            r = numpy.NaN
        return r, "bottomhat + entropy + gaussian 0.5"

    def bottomhat__entropy__gaussian_1(im, mask=None):
        try:
            r = FMs.ss(skif.rank.bottomhat(skif.rank.entropy(skif.gaussian_filter(im, 1), FMs.structureElement), FMs.structureElement), mask)
        except ValueError as e:
            r = numpy.NaN
        return r, "bottomhat + entropy + gaussian 1.0"

    def bottomhat__entropy__gaussian_2(im, mask=None):
        try:
            r = FMs.ss(skif.rank.bottomhat(skif.rank.entropy(skif.gaussian_filter(im, 2), FMs.structureElement), FMs.structureElement), mask)
        except ValueError as e:
            r = numpy.NaN
        return r, "bottomhat + entropy + gaussian 2.0"

    def bottomhat__entropy__gaussian_5(im, mask=None):
        try:
            r = FMs.ss(skif.rank.bottomhat(skif.rank.entropy(skif.gaussian_filter(im, 5), FMs.structureElement), FMs.structureElement), mask)
        except ValueError as e:
            r = numpy.NaN
        return r, "bottomhat + entropy + gaussian 5.0"

    def gaussian_gradient_0_5(im, mask=None):
        try:
            r = FMs.ss(ndfilt.gaussian_gradient_magnitude(im, 0.5), mask)
        except ValueError as e:
            r = numpy.NaN
        return r, "gaussian gradient magnitude 0.5"

    def gaussian_gradient_1(im, mask=None):
        try:
            r = FMs.ss(ndfilt.gaussian_gradient_magnitude(im, 1.0), mask)
        except ValueError as e:
            r = numpy.NaN
        return r, "gaussian gradient magnitude 1.0"

    def median_2__gaussian_gradient_0_5(im, mask=None):
        try:
            r = FMs.ss(ndfilt.gaussian_gradient_magnitude(ndfilt.median_filter(im, size=2), 0.5), mask)
        except ValueError as e:
            r = numpy.NaN
        return r, "median 2 + gaussian gradient magnitude 0.5"

    def median_2__gaussian_gradient_1(im, mask=None):
        try:
            r = FMs.ss(ndfilt.gaussian_gradient_magnitude(ndfilt.median_filter(im, size=2), 1.0), mask)
        except ValueError as e:
            r = numpy.NaN
        return r, "median 2 + gaussian gradient magnitude 1.0"

    def median_4__gaussian_gradient_0_5(im, mask=None):
        try:
            r = FMs.ss(ndfilt.gaussian_gradient_magnitude(ndfilt.median_filter(im, size=4), 0.5), mask)
        except ValueError as e:
            r = numpy.NaN
        return r, "median 4 + gaussian gradient magnitude 0.5"

    def median_4__gaussian_gradient_1(im, mask=None):
        try:
            r = FMs.ss(ndfilt.gaussian_gradient_magnitude(ndfilt.median_filter(im, size=4), 1.0), mask)
        except ValueError as e:
            r = numpy.NaN
        return r, "median 4 + gaussian gradient magnitude 1.0"

    def brennerh(im, mask=None):
        try:
            r = FMs.ss(brenner(im, 'h'), mask)
        except ValueError as e:
            r = numpy.NaN
        return r, "brenner h"

    def brennerv(im, mask=None):
        try:
            r = FMs.ss(brenner(im, 'v'), mask)
        except ValueError as e:
            r = numpy.NaN
        return r, "brenner v"

    def brennervh(im, mask=None):
        try:
            r = FMs.ss(brennervh(im), mask)
        except ValueError as e:
            r = numpy.NaN
        return r, "brenner vh"

    def median_2__brennerh(im, mask=None):
        try:
            r = FMs.ss(brenner(ndfilt.median_filter(im, size=2), 'h'), mask)
        except ValueError as e:
            r = numpy.NaN
        return r, "median 2 + brenner h"

    def median_2__brennerv(im, mask=None):
        try:
            r = FMs.ss(brenner(ndfilt.median_filter(im, size=2), 'v'), mask)
        except ValueError as e:
            r = numpy.NaN
        return r, "median 2 + brenner v"

    def median_2__brennervh(im, mask=None):
        try:
            r = FMs.ss(brennervh(ndfilt.median_filter(im, size=2)), mask)
        except ValueError as e:
            r = numpy.NaN
        return r, "median 2 + brenner vh"

    def median_4__brennerh(im, mask=None):
        try:
            r = FMs.ss(brenner(ndfilt.median_filter(im, size=4), 'h'), mask)
        except ValueError as e:
            r = numpy.NaN
        return r, "median 4 + brenner h"

    def median_4__brennerv(im, mask=None):
        try:
            r = FMs.ss(brenner(ndfilt.median_filter(im, size=4), 'v'), mask)
        except ValueError as e:
            r = numpy.NaN
        return r, "median 4 + brenner v"

    def median_4__brennervh(im, mask=None):
        try:
            r = FMs.ss(brennervh(ndfilt.median_filter(im, size=4)), mask)
        except ValueError as e:
            r = numpy.NaN
        return r, "median 4 + brenner vh"

    fmFuncs = [sobel_h,
               sobel_h__bilat_denoise,
               sobel_v,
               sobel_v__bilat_denoise,
#              canny,
               bottomhat,
               bottomhat__gaussian_0_5,
               bottomhat__gaussian_1,
               bottomhat__gaussian_2,
               bottomhat__gaussian_5,
               tophat,
               tophat__gaussian_0_5,
               tophat__gaussian_1,
               tophat__gaussian_2,
               tophat__gaussian_5,
               entropy,
               entropy__gaussian_0_5,
               entropy__gaussian_1,
               entropy__gaussian_2,
               entropy__gaussian_5,
               tophat__entropy,
               tophat__entropy__gaussian_0_5,
               tophat__entropy__gaussian_1,
               tophat__entropy__gaussian_2,
               tophat__entropy__gaussian_5,
               bottomhat__entropy,
               bottomhat__entropy__gaussian_0_5,
               bottomhat__entropy__gaussian_1,
               bottomhat__entropy__gaussian_2,
               bottomhat__entropy__gaussian_5]

    def all(ftable):
        rtable = None
        for fm in FMs.fmFuncs:
            rtable = computeFocusMeasure(ftable, rtable, fm)
        return rtable

    def easyAll(path, prefix):
        ftable = lsOrdered(path, prefix)
        rtable = FMs.all(ftable)
        storePath = Path(path) / (prefix + '.hdf5')
        store = pandas.HDFStore(str(storePath))
        store['rtable'] = rtable
        store['index'] = pandas.Series(ftable.index)

def forkFunc(stdoutLock, fmFuncs, imageFileNames, mask):
    for imageFileName in imageFileNames:
        image = skio.imread(str(imageFileName))
        skip = False
        if image.dtype != numpy.float32 and image.dtype != numpy.float64:
            if image.dtype != numpy.uint16:
                with stdoutLock:
                    print(image.dtype, '{},SKIPPED (unsupported format)'.format(str(imageFileName)))
                    continue
            image = (image / 65535).astype(numpy.float32)
        for fm in fmFuncs:
            result, fmName = fm(image, mask)
            with stdoutLock:
                print('{},{},{}'.format(str(imageFileName), fmName, result))

def runProcessPile(stdoutLock, fmFuncs, imageFileNames, maskFileName):
    mask = (skio.imread(str(maskFileName)) == 0)
    imageFileNames = numpy.array(imageFileNames)
    processes = [Process(target=forkFunc, args=(stdoutLock, fmFuncs, chunk, mask)) for chunk in numpy.array_split(imageFileNames, 4)]
    for process in processes:
        process.daemon = True
        process.start()
    return processes

if __name__ == '__main__':
    fmFuncs = [FMs.gaussian_gradient_0_5,
               FMs.gaussian_gradient_1,
               FMs.median_2__gaussian_gradient_0_5,
               FMs.median_2__gaussian_gradient_1,
               FMs.median_4__gaussian_gradient_0_5,
               FMs.median_4__gaussian_gradient_1,
               FMs.sobel_h,
               FMs.sobel_v,
               FMs.brennerh,
               FMs.brennerv,
               FMs.brennervh,
               FMs.median_2__brennerh,
               FMs.median_2__brennerv,
               FMs.median_2__brennervh,
               FMs.median_4__brennerh,
               FMs.median_4__brennerv,
               FMs.median_4__brennervh]

    stdoutLock = Lock()
    with open('/mnt/scopearray/autofocus/weekend/migsdat_scopemachine.pickle', 'rb') as f:
        migsdat = pickle.load(f)
    imageFileNames = []
    for groupName, scoreableImages in migsdat.items():
        for scoreableImage in scoreableImages:
            if scoreableImage.score is not None:
                if str(scoreableImage.fileName).find('/5x/') != -1 or str(scoreableImage.fileName).find('\/5x\/') != -1:
                    imageFileNames.append(scoreableImage.fileName)
    processes = runProcessPile(stdoutLock, fmFuncs, imageFileNames, Path('/mnt/scopearray/autofocus/weekend/5x_mask.png'))
    imageFileNames = []
    for groupName, scoreableImages in migsdat.items():
        for scoreableImage in scoreableImages:
            if scoreableImage.score is not None:
                if str(scoreableImage.fileName).find('/10x/') != -1 or str(scoreableImage.fileName).find('\/10x\/') != -1:
                    imageFileNames.append(scoreableImage.fileName)
    processes.extend(runProcessPile(stdoutLock, fmFuncs, imageFileNames, Path('/mnt/scopearray/autofocus/weekend/10x_mask.png')))
    for process in processes:
        process.join()
