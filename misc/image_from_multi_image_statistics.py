from pathlib import Path
import numpy
import skimage.io as skio
import skimage.transform
for function in ('imread', 'imsave', 'imread_collection'):
    skio.use_plugin('freeimage', function)
import re

def average_all_in(path, regex):
    imageFileNames = []
    for subdir in Path(path).glob('**'):
        if re.search(regex, str(subdir)):
            for png in subdir.glob('*.png'):
                imageFileNames.append(str(png))
    return average_images(imageFileNames)

def average_images(imageFileNames, crop=None, downsample_factor=None, gaussian_size=None):
    def _get(imageFileName):
        if type(imageFileName) is not str:
            imageFileName = str(imageFileName)
        print(imageFileName)
        im = skio.imread(imageFileName).astype(numpy.float32) / 65535
        if crop is not None:
            im = im[:crop[0], :crop[1]]
        if downsample_factor is not None:
            im = skimage.transform.downscale_local_mean(im, (downsample_factor, downsample_factor))
        if gaussian_size is not None:
            im = skimage.filter.gaussian_filter(im, gaussian_size)
        im *= 65535
        im = im.astype(numpy.uint16)
        return im
    imageCount = len(imageFileNames)
    if imageCount == 0:
        return None
    average32 = _get(imageFileNames[0]).astype(numpy.uint32)
    for imageFileName in imageFileNames[1:]:
        average32 += _get(imageFileName)
    return average32 / imageCount

def generate_running_percentile_difference(percentile=20, run_length=10, crop=None):
    """A specialized generator that outputs None for each image_or_image_fpath sent until sufficient
    history has accumulated, at which point a running percentile difference image is outputted for
    each image_or_image_fpath sent."""
    if run_length < 1:
        raise ValueError('run_length must be at least 1.')
    next_running_image_replace_idx = 0
    idx = 0
    difference = None
    while 1:
        image_or_image_fpath = yield difference
        if image_or_image_fpath is None:
            break

        if issubclass(type(image_or_image_fpath), Path) or type(image_or_image_fpath) is str:
            image = skio.imread(str(image_or_image_fpath))
        else:
            image = image_or_image_fpath

        if crop:
            image = image[:crop[0], :crop[1]]

        if idx == 0:
            image_shape = image.shape
            running_images = numpy.zeros((run_length,) + image_shape, dtype=numpy.uint16)
        else:
            if image.shape != image_shape:
                e = 'image_or_image_fpath index {} ({}) has shape {}, '.format(idx, str(image_or_image_fpath), image.shape)
                e+= 'which differs from image_or_image_fpath index 0\'s shape of {}.'.format(image_shape)
                raise ValueError(e)

        if idx >= run_length:
            # We have enough history to compute a running median and associated difference image
            median = numpy.percentile(running_images, percentile, axis=0, interpolation='nearest')
            difference = numpy.abs(median.astype(numpy.int32) - image.astype(numpy.int32)).astype(numpy.uint16)

        running_images[next_running_image_replace_idx, :, :] = image
        next_running_image_replace_idx += 1
        if next_running_image_replace_idx == run_length:
            next_running_image_replace_idx = 0
        idx += 1

def generate_running_percentile_differences(images_or_image_fpaths, percentile=20, run_length=10, crop=None):
    """A normal generator that outputs None for the first run_length elements of images_or_image_fpaths, and
    a running percentile difference image for each subsequent element."""
    running_percentile_difference_generator = generate_running_percentile_difference(percentile, run_length, crop)
    next(running_percentile_difference_generator)
    for image_or_image_fpath in images_or_image_fpaths:
        yield running_percentile_difference_generator.send(image_or_image_fpath)
