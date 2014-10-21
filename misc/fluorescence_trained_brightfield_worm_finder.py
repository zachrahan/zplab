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

import misc._texture_analysis._texture_analysis as texan

def overlayCenterLineOnWorm(imageFPath):
    imageFPath = Path(imageFPath)
    im_bf = skio.imread(str(imageFPath))
    im_centerLine = skio.imread(str(imageFPath.parent / 'fluo_worm_mask_skeleton.png'))
    return im_bf ^ ((im_centerLine > 0).astype(numpy.uint16) * 65535)

def cropToFluorescenceMask(image, imageFPath):
    imageFPath = Path(imageFPath)
    im_mask = skio.imread(str(imageFPath.parent / 'fluo_worm_mask.png')) > 0
    labels = skimage.measure.label(im_mask)
    regions = skimage.measure.regionprops(labels)
    if len(regions) == 0:
        print('warning: mask is empty')
    else:
        if len(regions) > 1:
            print('warning: mask contains multiple regions')
        else:
            bb = regions[0].bbox
            return numpy.copy(image[bb[0]:bb[2]+1, bb[1]:bb[3]+1])

def selectRandomPoints(imageFPath, centerLinePointCount, nonWormPointCount):
    centerLinePoints = []
    nonWormPoints = []
    imageFPath = Path(imageFPath)
    im_mask = skio.imread(str(imageFPath.parent / 'fluo_worm_mask.png')) > 0
    # Dilate mask out substantially so that non-worm pixels we select are not adjacent to the worm
    im_mask = scipy.ndimage.morphology.binary_dilation(im_mask, iterations=100)
    im_centerline = skio.imread(str(imageFPath.parent / 'fluo_worm_mask_skeleton.png')) > 0
    labels = skimage.measure.label(im_centerline)
    regions = skimage.measure.regionprops(labels)
    if len(regions) == 0:
        raise RuntimeError('Mask skeleton image contains no regions.')
    else:
        if len(regions) > 1:
            raise RuntimeError('Mask skeleton image contains multiple regions.')
        else:
            coords = regions[0].coords
            if centerLinePointCount > len(coords):
                print('warning: centerLinePointCount exceeds number of pixels in skeleton... ' + \
                      'All skeleton points will be returned without duplication, which is still ' + \
                      'fewer points than requested.')
                centerLinePointCount = len(coords)
            centerLinePoints = coords[numpy.random.choice(range(len(coords)), size=centerLinePointCount, replace=False)]
            while len(nonWormPoints) < nonWormPointCount:
                y = numpy.random.randint(im_mask.shape[0])
                x = numpy.random.randint(im_mask.shape[1])
                if im_mask[y, x] or math.sqrt((y - 1079.5)**2 + (x - 1279.5)**2) > 1000 or (y, x) in nonWormPoints:
                    continue
                nonWormPoints.append((y, x))
    return numpy.array(centerLinePoints, dtype=numpy.uint32), numpy.array(nonWormPoints, dtype=numpy.uint32)

arMask = None

def makeFeatureVector(imf, patchWidth, point):
#   def gabor(theta):
#       g = skimage.filter.gabor_filter(imf[point[0]-filterBoxOffset:point[0]+filterBoxOffset,
#                                           point[1]-filterBoxOffset:point[1]+filterBoxOffset],
#                                       frequency=0.1, theta=theta)
#       return (g[0][responseBoxOffset:responseBoxOffset+patchWidth,
#                    responseBoxOffset:responseBoxOffset+patchWidth],
#               g[1][responseBoxOffset:responseBoxOffset+patchWidth,
#                    responseBoxOffset:responseBoxOffset+patchWidth])
#   filterBoxOffset = patchWidth / 2 + 10
#   responseBoxOffset = patchWidth / 2
#   return numpy.array((gabor(0), gabor(math.pi/4))).ravel()
    global arMask
    if arMask is None or arMask.shape != (patchWidth, patchWidth):
        arMask = numpy.diag(numpy.ones((patchWidth, patchWidth), dtype=numpy.uint8))
        arMask+= arMask[::-1]
        arMask = ~arMask.astype(numpy.bool)
    boxOffset = int(patchWidth / 2)
    masked = numpy.ma.array(imf[point[0]-boxOffset : point[0]+boxOffset,
                                point[1]-boxOffset : point[1]+boxOffset],
                            mask=arMask)
    return masked.compressed()

def makeTrainingTestingFeatureVectorsForImage(imageFPath, patchWidth, centerLineCount, nonWormCount):
    imf = skimage.exposure.equalize_adapthist(skio.imread(str(imageFPath))).astype(numpy.float32)
    centerLinePoints, nonWormPoints = selectRandomPoints(imageFPath, centerLineCount, nonWormCount)
    data = []
    targets = []
    for p in centerLinePoints:
        data.append(makeFeatureVector(imf, patchWidth, p))
        targets.append(True)
    for p in nonWormPoints:
        data.append(makeFeatureVector(imf, patchWidth, p))
        targets.append(False)
    return (data, targets)

def showWormWithCenterLine(risWidget, imageFPath):
    risWidget.showImage(overlayCenterLineOnWorm(imageFPath))

def loadTrainingAndTestingDataAndTargets(dataAndTargetDbFPath):
    with open(str(dataAndTargetDbFPath), 'rb') as f:
        dataAndTargetDb = pickle.load(f)
    learnImageFPaths = set(dataAndTargetDb.keys())
    testImageFPaths = {i for i in numpy.random.choice(list(learnImageFPaths), size=91, replace=False)}
    learnImageFPaths -= testImageFPaths
    learnImageFPaths = list(learnImageFPaths)
    testImageFPaths = list(testImageFPaths)
    testTargets = [target for targetList in [dataAndTargetDb[fpath][1] for fpath in testImageFPaths] for target in targetList]
    learnTargets = [target for targetList in [dataAndTargetDb[fpath][1] for fpath in learnImageFPaths] for target in targetList]
    testData = [vector for vectorList in [dataAndTargetDb[fpath][0] for fpath in testImageFPaths] for vector in vectorList]
    learnData = [vector for vectorList in [dataAndTargetDb[fpath][0] for fpath in learnImageFPaths] for vector in vectorList]
    return (learnData, learnTargets, testData, testTargets)

def writeLibSvmDataAndTargetsFile(data, targets, libSvmDataAndTargetsFileFPath):
    '''Note: If file at path libSvmDataAndTargetsFileFPath exists, this function will attempt to overwrite it.'''
    if len(data) != len(targets):
        raise ValueError("len(data) != len(targets)")
    with open(str(libSvmDataAndTargetsFileFPath), 'w') as libSvmDataAndTargetsFile:
        for vector, target in zip(data, targets):
            if target:
                l = '1 '
            else:
                l = '0 '
            for elementIdx, element in enumerate(vector, 1):
                l += '{}:{} '.format(elementIdx, element)
            l += '\n'
            libSvmDataAndTargetsFile.write(l)


from misc.manually_score_images import ManualImageScorer

class ManualCenterLineScorer(ManualImageScorer):
    def _getImage(self, imageFPath):
        return cropToFluorescenceMask(overlayCenterLineOnWorm(imageFPath), imageFPath)

def averageImages(images):
    imageCount = len(images)
    if imageCount == 0:
        return None
    average32 = images[0].astype(numpy.uint32)
    for image in images[1:]:
        average32 += image
    return average32 / imageCount

def findWormAgainstBackground(rw, images, lowpassSigma=3, erosionThresholdPercentile=97.9, propagationThresholdPercentile=97.7):
    if len(images) < 3:
        raise ValueError('At least 3 images are required.')
    im = numpy.abs(averageImages(images[:-1]).astype(numpy.float32) - images[-1])
#   rw.showImage(im.astype(numpy.uint16))
#   input()
#   lowpass = scipy.ndimage.gaussian_filter(im, lowpassSigma)
#   highpass = numpy.abs(im - lowpass)
#   im = numpy.abs(im - highpass)
    im = scipy.ndimage.median_filter(im, size=5)
#   rw.showImage(im.astype(numpy.uint16))
#   input()
#   foos = []

    for i in range(10):
        eroded = scipy.ndimage.morphology.binary_erosion(im > numpy.percentile(im, erosionThresholdPercentile), iterations=5)
        propagated = scipy.ndimage.morphology.binary_propagation(eroded, mask = im > numpy.percentile(im, propagationThresholdPercentile))
        dilated = scipy.ndimage.morphology.binary_dilation(propagated, iterations=5)
        imm = scipy.ndimage.morphology.binary_fill_holes(dilated)
        rw.showImage(imm)

        immlabels = skimage.measure.label(imm)
        immregions = skimage.measure.regionprops(immlabels)
        if len(immregions) > 0:
            immregions.sort(key=lambda region: region.area, reverse=True)
            r = immregions[0]
            mask = numpy.zeros(im.shape).astype(numpy.bool)
            a, b = r.bbox[0], r.bbox[1]
            aw, bw = r.bbox[2] - r.bbox[0], r.bbox[3] - r.bbox[1]
            mask[a:a+aw, b:b+bw] = r.image
            return im.astype(numpy.uint16), mask
#       foos.append(imm)
        print(erosionThresholdPercentile, propagationThresholdPercentile)

        erosionThresholdPercentile -= 0.5
        propagationThresholdPercentile -= 0.5
#   return foos

def findWormInImage(im, classifier, patchWidth):
    imf = skimage.exposure.equalize_adapthist(im).astype(numpy.float32)
    filterBoxWidth = patchWidth + 10
    halfFilterBoxWidth = filterBoxWidth / 2
    ycount = int(imf.shape[0] / filterBoxWidth)
    xcount = int(imf.shape[1] / filterBoxWidth)
    mask = numpy.zeros((ycount, xcount), dtype=numpy.bool)
    xycount = ycount * xcount
    xyindex = 0
    for yindex in range(ycount):
        y = halfFilterBoxWidth + yindex * filterBoxWidth
        for xindex in range(xcount):
            x = halfFilterBoxWidth + xindex * filterBoxWidth
            vector = makeFeatureVector(imf, patchWidth, (y, x))
            mask[yindex, xindex] = False if len(vector) == 0 else classifier.predict(vector)
            xyindex += 1
            print('{}%'.format(100 * xyindex / xycount))
    return mask

def findWormInImage_z(im, classifier):
    pass

def _processFunction(imageIndex, imageFPath, centerLineSampleCount, nonWormSampleCount, patchWidth):
    try:
        data, targets = makeTrainingTestingFeatureVectorsForImage(imageFPath, patchWidth, centerLineSampleCount, nonWormSampleCount)
        return imageIndex, imageFPath, data, targets
    except Exception as processException:
        processException.imageFPath = imageFPath
        raise processException

if __name__ == '__main__':
    import argparse
    argparser = argparse.ArgumentParser(description='Brightfield worm finder fluorescence generator of data & target dataset for training & testing.')
    argparser.add_argument('--imageCenterLineDb', required=True)
    argparser.add_argument('--dataAndTargetScratchDb', required=True)
    argparser.add_argument('--dataAndTargetDb', required=True)
    argparser.add_argument('--centerLineSampleCount', default=5, type=int)
    argparser.add_argument('--nonWormSampleCount', default=20, type=int)
    argparser.add_argument('--patchWidth', default=8, type=int)
    args = argparser.parse_args()
    with open(args.imageCenterLineDb, 'rb') as f:
        imageCenterLineDb = pickle.load(f)
        # Use only image sets (bf, fluo, mask, skeleton) whose skeleton passed manual examination (skeleton properly overlays the worm center
        # line without branching)
        imageFPaths = sorted([imageFPath for imageFPath, score in imageCenterLineDb.items() if score == 1])
        del imageCenterLineDb
    dataAndTargetDb = dict()
    # Attempt to load data in order to resume previously interrupted or failed run
    try:
        with open(args.dataAndTargetScratchDb, 'rb') as f:
            while True:
                imageFPath, data, targets = pickle.load(f)
                if imageFPath in dataAndTargetDb:
                    raise RuntimeError('"{}" appears multiple times in dataAndTargetScratchDb file ("{}").'.format(str(imageFPath), args.dataAndTargetScratchDb))
                dataAndTargetDb[imageFPath] = (data, targets)
    except (FileNotFoundError, EOFError):
        pass

    def processCompletionCallback(processReturn):
        imageIndex, imageFPath, data, targets = processReturn
        if imageFPath in dataAndTargetDb:
            raise RuntimeError('Multiple data & target datasets generated for "{}".'.format(str(imageFPath)))
        dataAndTargetDb[imageFPath] = [data, targets]
        pickle.dump((imageFPath, data, targets), dataAndTargetScratchDbFile)
        dataAndTargetScratchDbFile.flush()
        print('{}%'.format(100 * (imageIndex + 1) / len(imageFPaths)))

    def processExceptionCallback(processException):
        try:
            imageFPath = processException.imageFPath
            del processException.imageFPath
            print('warning: processing failed for "{}" with exception:'.format(str(imageFPath)), processException)
        except AttributeError:
            print('warning: processing failed for "UNKOWN FILE" with exception:', processException)

    with open(args.dataAndTargetScratchDb, 'ab') as dataAndTargetScratchDbFile:
        with multiprocessing.Pool(multiprocessing.cpu_count() + 1) as pool:
            asyncResults = []
            for imageIndex, imageFPath in enumerate(imageFPaths):
                if imageFPath not in dataAndTargetDb:
                    asyncResults.append(pool.apply_async(_processFunction,
                                                         (imageIndex, imageFPath, args.centerLineSampleCount, args.nonWormSampleCount, args.patchWidth),
                                                         callback=processCompletionCallback,
                                                         error_callback=processExceptionCallback))
            pool.close()
            pool.join()

    print('Done!  Writing data & target db ("{}")...'.format(args.dataAndTargetDb))
    with open(args.dataAndTargetDb, 'wb') as f:
        pickle.dump(dataAndTargetDb, f)
    print('Data & target db written.  Deleting scratch db ("{}")...'.format(args.dataAndTargetScratchDb))
    Path(args.dataAndTargetScratchDb).unlink()
    print('Scratch db deleted.  Exiting...')
