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
import json
import html
import numpy
from pathlib import Path
from PyQt5 import Qt
import sys
import time
from .extensible_video_maker import ControlPane, ExtensibleVideoMaker, GV

class ExtensibleVideoMakerMultiwellSample(ExtensibleVideoMaker):
    LABEL_HEIGHT = 60
    BUFFER_WIDTH = 10
    FRAME_WIDTH = 4
    IMAGE_SIZE = Qt.QSize(2560, 2160)

    class Well:
        def __init__(self, title, patterns, dpath, channel_names=None):
            dpath = Path(dpath)
            self.title = title
            self.channel_names = channel_names
            self.patterns = patterns
            self.imfpath_sets = [sorted(dpath.glob(pattern)) for pattern in patterns]

    def __init__(self,
                 video_out_fpath,
                 wells,
                 scale_factor=0.5,
                 video_fps=10,
                 parent=None,
                 ControlPaneClass=ControlPane,
                 GSClass=Qt.QGraphicsScene,
                 GVClass=GV):
        assert len(wells) > 0
        assert len(wells[0].imfpath_sets) > 0
        assert len(wells[0].imfpath_sets[0]) > 0
        self.wells = wells
        super().__init__(video_out_fpath, scale_factor, video_fps, parent, ControlPaneClass, GSClass, GVClass)
        self.t0 = datetime.datetime.fromtimestamp(wells[0].imfpath_sets[0][0].stat().st_mtime)

    def verify_well_channel_name_and_image_count_uniform_cardinality(self):
        if self.wells:
            c = len(self.wells[0].imfpath_sets[0])
            for well in self.wells:
                if well.channel_names is not None and len(well.channel_names) != len(well.imfpath_sets):
                    raise ValueError('Mismatch between number of channel names ({}) and patterns ({}) for well "{}".'.format(len(well.channel_names), len(well.imfpath_sets), well.title))
                for imfpath_set_idx, imfpath_set in enumerate(well.imfpath_sets):
                    if len(imfpath_set) != c:
                        raise ValueError('Got {} images for well "{}", pattern "{}".  However, {} were expected.  If support is needed for missing images/incomplete timepoints, additional logic must be implemented to detect '
                                         'that a specific expected image name is missing and display "file not found" in place of the missing image.'.format(len(imfpath_set), well.title, well.patterns[imfpath_set_idx], c))

    def make_title_label_widget_and_item(self, text=html.escape('<TITLE TEXT>'), fg_color=None, bg_color=None, font=None, rect=None):
        if fg_color is None:
            fg_color = Qt.QColor(Qt.Qt.white)
        if bg_color is None:
            bg_color = Qt.QColor(0,0,0,0)
        if font is None:
            font = Qt.QFont('Courier')
            font.setPixelSize(self.LABEL_HEIGHT)
        widget = Qt.QLabel()
        widget.setFont(font)
        widget.setTextFormat(Qt.Qt.RichText)
        widget.setText(text)
        widget.setAlignment(Qt.Qt.AlignHCenter | Qt.Qt.AlignVCenter)
        palette = widget.palette()
        palette.setColor(Qt.QPalette.Foreground, fg_color)
        palette.setColor(Qt.QPalette.Background, bg_color)
        widget.setPalette(palette)
        item = self.gs.addWidget(widget)
        if rect is not None:
            widget.resize(rect.size())
            item.setPos(rect.topLeft())
        return widget, item

    def populate_scene(self):
        self.verify_well_channel_name_and_image_count_uniform_cardinality()
        if any(well.channel_names is not None for well in self.wells):
            unified_channel_labels = True
            if len(self.wells) > 1:
                 well_it = iter(self.wells)
                 well0names = next(well_it).channel_names
                 for well in well_it:
                     if well.channel_names != well0names:
                         unified_channel_labels = False
        i_s= self.IMAGE_SIZE
        fw = self.FRAME_WIDTH
        bw = self.BUFFER_WIDTH
        hbw= int(bw / 2)
        lh = self.LABEL_HEIGHT
        x = 0
        def make_channel_labels(well):
            nonlocal x
            y = hbw + lh + hbw
            h = i_s.height() + bw
            well.channel_labels = []
            for channel_name in well.channel_names:
                w, i = self.make_title_label_widget_and_item(channel_name)
                i.setRotation(-90)
                i.setPos(x, y + h)
                w.resize(h, hbw + lh + hbw)
                well.channel_labels.append((w, i))
                y += bw + i_s.height()
            x += hbw + lh + hbw
        if unified_channel_labels:
            make_channel_labels(self.wells[0])
        frame_pen = Qt.QPen(Qt.Qt.NoPen)
        frame_brush = Qt.QBrush(Qt.QColor(Qt.Qt.gray))
        for well in self.wells:
            well.frames = []
            well.iis = []
            well.titles = []
            y = 0
            well.title_widget, well.title_item = self.make_title_label_widget_and_item(rect=Qt.QRect(x, y, fw + i_s.width() + fw, hbw + lh + hbw))
            y += hbw + lh + hbw
            for channel_idx in range(len(well.patterns)):
                if not unified_channel_labels and well.channel_names is not None:
                    make_channel_labels(well)
                frame = self.gs.addRect(x, y, fw + i_s.width() + fw, fw + i_s.height() + fw, frame_pen, frame_brush)
                frame.setZValue(-1)
                well.frames.append(frame)
                ii = self.gs.addPixmap(Qt.QPixmap(i_s))
                ii.setPos(x + fw, y + fw)
                well.iis.append(ii)
                y += i_s.height() + bw
            x += i_s.width() + bw
        self.gs.setSceneRect(0, 0, x, y)

    def update_scene_for_current_frame(self):
        frame_idx = self.frame_index + 1
        if frame_idx >= len(self.wells[0].imfpath_sets[0]):
            return False
        for well in self.wells:
            ts = datetime.datetime.fromtimestamp(well.imfpath_sets[0][frame_idx].stat().st_mtime)
            ts_str = ts.isoformat()[:19]
            delta_str = str(ts - self.t0)
            well.title_widget.setText('<b>{}</b> {} (<b>+ {}</b>)'.format(*map(html.escape, [well.title, ts_str, delta_str])))
            for ii, imfpath_set in zip(well.iis, well.imfpath_sets):
                self.read_image_file_into_qpixmap_item(imfpath_set[frame_idx], ii, self.IMAGE_SIZE)
        return True

if __name__ == "__main__":
    import sys
    app = Qt.QApplication(sys.argv)
    if len(sys.argv) != 2:
        raise ValueError("\n\n\n\nPlease supply a single argument containing json, for example (note leading ' beginning multiline argument):\n\n"
                         """python -m misc.extensible_video_maker_multiwell_usage_sample '""" '\n'
                         """{"wells": [{"channel_names": ["BF", "GFP"], "patterns": ["2015*bf.png", "2015*gfp.png"], "title": "Well 0", "dpath": "/mnt/scopearray/Earley_Brian/hw1360_ng/00"},""" '\n'
                         """           {"channel_names": ["BF", "GFP"], "patterns": ["2015*bf.png", "2015*gfp.png"], "title": "Well 11", "dpath": "/mnt/scopearray/Earley_Brian/hw1360_ng/11"},""" '\n'
                         """           {"channel_names": ["BF", "GFP"], "patterns": ["2015*bf.png", "2015*gfp.png"], "title": "Well 14", "dpath": "/mnt/scopearray/Earley_Brian/hw1360_ng/14"}],""" '\n'
                         """ "output_fpath": "/mnt/scopearray/Earley_Brian/hw1360_ng/wells_0_11_14.mp4",""" '\n'
                         """ "scale_factor": 0.333333}'""" '\n\n'
                         'Alternatively, the json may be located in a file specified with --json=filename as the only argument.\n'
                         'Omit the channel_names fields if vertical labels on the left side are not desired.\n'
                         'Omit the scale_factor field to use the default of 1/2.')
    if sys.argv[1].startswith('--file='):
        with open(sys.argv[1][len('--file='):]) as jf:
            js = jf.read()
    else:
        js = sys.argv[1]
    j = json.loads(js)
    output_fpath = j['output_fpath']
    wells = [ExtensibleVideoMakerMultiwellSample.Well(**e) for e in j['wells']]
    vm = ExtensibleVideoMakerMultiwellSample(output_fpath, wells)
    if 'scale_factor' in j:
        vm.scale_factor = j['scale_factor']
    vm.setAttribute(Qt.Qt.WA_DeleteOnClose)
    vm.show()
    app.exec()
