import numpy
from PyQt5 import Qt
from ris_widget.ris_widget import RisWidget
import freeimage
import sys

if sys.platform == 'darwin':
#   im = freeimage.read('/Volumes/scopearray/pharyngeal_pumping_max_fps/pharyngeal_pumping_max_fps_010_0.274411275.png')
    im = freeimage.read('/Users/ehvatum/zplrepo/ris_widget/top_left_g.png')
elif sys.platform == 'linux':
    im = freeimage.read('/mnt/scopearray/pharyngeal_pumping_max_fps/pharyngeal_pumping_max_fps_010_0.274411275.png')

argv = sys.argv
app = Qt.QApplication(argv)
rw = RisWidget()
rw.show()
rw.image_data = im
app.exec_()
