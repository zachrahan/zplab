#!/usr/bin/env python3

# The MIT License (MIT)
#
# Copyright (c) 2015 WUSTL ZPLAB
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
# Authors: Erik Hvatum <ice.rikh@gmail.com>

import datetime
import numpy
from pathlib import Path
from PyQt5 import Qt
import sys
import time
from .extensible_video_maker import ControlPane, ExtensibleVideoMaker, GV

class ExtensibleVideoMakerSample(ExtensibleVideoMaker):
    def __init__(self,
                 experiment_title,
                 experiment_dpath,
                 video_out_fpath,
                 scale_factor=0.5,
                 video_fps=10,
                 parent=None,
                 ControlPaneClass=ControlPane,
                 GSClass=Qt.QGraphicsScene,
                 GVClass=GV):
        super().__init__(video_out_fpath, scale_factor, video_fps, parent, ControlPaneClass, GSClass, GVClass)
        self.experiment_title = experiment_title
        experiment_dpath = Path(experiment_dpath)
        assert experiment_dpath.exists()
        bfs = sorted(experiment_dpath.glob('2015*bf.png'))
        gfps = sorted(experiment_dpath.glob('2015*gfp.png'))
        assert len(bfs) > 0 and len(gfps) > 0
        self.image_fpaths = list(zip(bfs, gfps))
        self.t0 = datetime.datetime.fromtimestamp(bfs[0].stat().st_ctime)

    def populate_scene(self):
        title_font = Qt.QFont('Courier')
        title_font_size = 60
        title_font.setPixelSize(title_font_size)
        self.title_label = Qt.QLabel()
        self.title_label.setFont(title_font)
        self.title_label.setTextFormat(Qt.Qt.PlainText)
        self.title_label.setText('<TITLE TEXT>')
        self.title_label.setAlignment(Qt.Qt.AlignHCenter | Qt.Qt.AlignVCenter)
        title_palette = self.title_label.palette()
        title_palette.setColor(Qt.QPalette.Foreground, Qt.QColor(Qt.Qt.white))
        title_palette.setColor(Qt.QPalette.Background, Qt.QColor(0,0,0,0))
        self.title_label.setPalette(title_palette)
        b = 10
        w = b + 2560 + b + 2560 + b
        h = b + title_font_size + b + 2160 + b
        self.gs.setSceneRect(0, 0, w, h)
        self.title_label_item = self.gs.addWidget(self.title_label)
        self.title_label.resize(w, b + title_font_size + b)
        self.title_label_item.setPos(0, 0)
        self.bf_ii = self.gs.addPixmap(Qt.QPixmap(2560, 2160))
        self.bf_ii.setPos(b, b + title_font_size + b)
        self.gfp_ii = self.gs.addPixmap(Qt.QPixmap(2560, 2160))
        self.gfp_ii.setPos(b + 2560 + b, b + title_font_size + b)

    def update_scene_for_current_frame(self):
        frame_idx = self._displayed_frame_idx + 1
        if frame_idx >= len(self.image_fpaths):
            return False
        bf_fpath, gfp_fpath = self.image_fpaths[frame_idx]
        ts = datetime.datetime.fromtimestamp(bf_fpath.stat().st_ctime)
        ts_str = ts.isoformat()[:19]
        delta_str = str(ts - self.t0)
        self.title_label.setText('{} {} (+ {})'.format(self.experiment_title, ts_str, delta_str))
        self.read_image_file_into_qpixmap_item(bf_fpath, self.bf_ii)
        self.read_image_file_into_qpixmap_item(gfp_fpath, self.gfp_ii)
        return True

if __name__ == "__main__":
    import sys
    app = Qt.QApplication(sys.argv)
    if len(sys.argv) < 2:
        raise ValueError('Please supply experiment directory path as the first parameter.')
    if len(sys.argv) < 3:
        raise ValueError('Please supply experiment title as the second parameter.')
    if len(sys.argv) < 4:
        raise ValueError('Please supply output video filename as the third parameter.')
    ExtensibleVideoMakerSample.EXPERIMENT_DPATH = Path(sys.argv[1])
    if not ExtensibleVideoMakerSample.EXPERIMENT_DPATH.exists():
        raise ValueError('Specified experiment directory path does not exist or is not accessible.')
    vm = ExtensibleVideoMakerSample(experiment_dpath=sys.argv[1], experiment_title=sys.argv[2], video_out_fpath=sys.argv[3])
    vm.setAttribute(Qt.Qt.WA_DeleteOnClose)
    vm.show()
    app.exec()
