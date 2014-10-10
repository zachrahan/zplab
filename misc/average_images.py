import numpy
from pathlib import Path
import re
from skimage import io as skio
from skimage import filter as skif
from skimage import transform as skit

def averageAllIn(path, regex):
    imageFileNames = []
    for subdir in Path(path).glob('**'):
        if re.search(regex, str(subdir)):
            for png in subdir.glob('*.png'):
                imageFileNames.append(str(png))
    return averageImages(imageFileNames)

def averageImages(imageFileNames):
    imageCount = len(imageFileNames)
    if imageCount == 0:
        return None
    average32 = _get(imageFileNames[0]).astype(numpy.uint32)
    for imageFileName in imageFileNames[1:]:
        average32 += _get(imageFileName)
    return average32 / imageCount

def _get(imageFileName):
    if type(imageFileName) is not str:
        imageFileName = str(imageFileName)
    print(imageFileName)
    im = skio.imread(imageFileName)[:2160,:2560].astype(numpy.float32) / 65535
#   im = skit.downscale_local_mean(im, (4, 4))
    im = skif.gaussian_filter(im, 8)
    im *= 65535
    im = im.astype(numpy.uint16)
    return im
