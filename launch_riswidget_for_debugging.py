#!/usr/bin/env python

import numpy
from PyQt5 import Qt
from ris_widget.ris_widget import RisWidget
import freeimage
import sys

if sys.platform == 'darwin':
    im = freeimage.read('/Volumes/scopearray/pharyngeal_pumping_max_fps/pharyngeal_pumping_max_fps_010_0.274411275.png')
#   im = freeimage.read('/Users/ehvatum/zplrepo/ris_widget/top_left_g.png')
elif sys.platform == 'linux':
#   im = freeimage.read('/home/ehvatum/2048.png')
    im = freeimage.read('/mnt/scopearray/pharyngeal_pumping_max_fps/pharyngeal_pumping_max_fps_010_0.274411275.png')
    oim = freeimage.read('/mnt/scopearray/Zhang_William/allyl_validation/light_0002/allyl_validation__light_0002_0008_bf.png')
elif sys.platform == 'win32':
    im = freeimage.read('C:/zplrepo/ris_widget/top_left_g.png')

argv = sys.argv
app = Qt.QApplication(argv)
rw = RisWidget()
rw.show()
rw.main_scene.image_stack.append_image(im)
#ioi = ImageOverlayItem(rw.image_scene.image_item, oim)
#
#hide_show_ioi_dlg = Qt.QWidget()
#hide_show_ioi_dlg.setLayout(Qt.QHBoxLayout())
#hide_show_ioi_dlg.show_button = Qt.QPushButton('show')
#hide_show_ioi_dlg.layout().addWidget(hide_show_ioi_dlg.show_button)
#hide_show_ioi_dlg.show_button.clicked.connect(ioi.show)
#hide_show_ioi_dlg.hide_button = Qt.QPushButton('hide')
#hide_show_ioi_dlg.layout().addWidget(hide_show_ioi_dlg.hide_button)
#hide_show_ioi_dlg.hide_button.clicked.connect(ioi.hide)
#hide_show_ioi_dlg.show()

#form_scene = rw.image_scene
#form_scene = rw.image_view_overlay_scene
#
#text_edit = form_scene.addWidget(Qt.QTextEdit())
#button = form_scene.addWidget(Qt.QPushButton('push me'))
#button.setStyle(Qt.QStyleFactory.create('Fusion'))
#button.setOpacity(0.5)
#layout = Qt.QGraphicsGridLayout()
#layout.addItem(text_edit, 0, 0)
#layout.addItem(button, 0, 1)
#form = Qt.QGraphicsWidget()
#form.setLayout(layout)
#form_scene.addItem(form)
#text_edit.widget().setText('foo bar baz')
#
#if form_scene is rw.image_view_overlay_scene:
#    rw.image_scene.installEventFilter(rw.image_view_overlay_scene)
#
#del form_scene

app.exec_()
