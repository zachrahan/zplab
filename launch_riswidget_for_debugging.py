import numpy
from PyQt5 import Qt
from ris_widget.ris_widget import RisWidget
import freeimage
import sys

if sys.platform == 'darwin':
    im = freeimage.read('/Volumes/scopearray/pharyngeal_pumping_max_fps/pharyngeal_pumping_max_fps_010_0.274411275.png')
#   im = freeimage.read('/Users/ehvatum/zplrepo/ris_widget/top_left_g.png')
elif sys.platform == 'linux':
    im = freeimage.read('/mnt/scopearray/pharyngeal_pumping_max_fps/pharyngeal_pumping_max_fps_010_0.274411275.png')

argv = sys.argv
app = Qt.QApplication(argv)
rw = RisWidget()
rw.show()
rw.image_data = im

#form_scene = rw.image_scene
form_scene = rw.image_view_overlay_scene

text_edit = form_scene.addWidget(Qt.QTextEdit())
button = form_scene.addWidget(Qt.QPushButton('push me'))
button.setStyle(Qt.QStyleFactory.create('Fusion'))
button.setOpacity(0.5)
layout = Qt.QGraphicsGridLayout()
layout.addItem(text_edit, 0, 0)
layout.addItem(button, 0, 1)
form = Qt.QGraphicsWidget()
form.setLayout(layout)
form_scene.addItem(form)
text_edit.widget().setText('foo bar baz')

if form_scene is rw.image_view_overlay_scene:
    rw.image_scene.installEventFilter(rw.image_view_overlay_scene)

del form_scene

app.exec_()
