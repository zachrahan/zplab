def _brenner(im, direction):
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

def brenner(im):
    imh = _brenner(im, 'h')
    imv = _brenner(im, 'v')
    return numpy.sqrt(imh**2 + imv**2)
