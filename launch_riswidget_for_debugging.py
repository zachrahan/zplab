import numpy
from skimage import io as skio
for function in ('imread', 'imsave', 'imread_collection'):
    skio.use_plugin('freeimage', function)
from PyQt5 import Qt
from ris_widget.ris_widget import RisWidget
from ris_widget import freeimage
import sys

im = skio.imread('/Volumes/scopearray/pharyngeal_pumping_max_fps/pharyngeal_pumping_max_fps_010_0.274411275.png')
#im = skio.imread('/Users/ehvatum/heic1015a.jpg')
#im = freeimage.read('/Users/ehvatum/heic1015a.jpg')
#im = freeimage.read('/Users/ehvatum/zplrepo/ris_widget/top_left.png')

argv = sys.argv
app = Qt.QApplication(argv)
rw = RisWidget()
rw.show()
rw.image_data = im
app.exec_()
