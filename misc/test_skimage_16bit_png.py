# Copyright 2014 WUSTL ZPLAB
# Erik Hvatum (ice.rikh@gmail.com)

import numpy
from pathlib import Path
import skimage.io as skio
for function in ('imread', 'imsave', 'imread_collection'):
    skio.use_plugin('freeimage', function)

imageRaw = numpy.arange(0, 65536, dtype=numpy.uint16).reshape(256, 256)
image = skio.Image(imageRaw)
imagePath = Path('/home/ehvatum/zplrepo/misc/im.png')
if imagePath.exists():
    imagePath.unlink()
skio.imsave(str(imagePath), image)

print('done')
