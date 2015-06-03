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

from PyQt5 import Qt
from .extensible_video_maker import ControlPane, ExtensibleVideoMaker, GV

class CallbackingVideoMaker(ExtensibleVideoMaker):
    def __init__(self,
                 video_out_fpath,
                 scale_factor=0.5,
                 video_fps=10,
                 populate_scene_callback,
                 update_scene_for_current_frame_callback,
                 parent=None,
                 ControlPaneClass=ControlPane,
                 GSClass=Qt.QGraphicsScene,
                 GVClass=GV):
        self.populate_scene_callback = populate_scene_callback
        self.update_scene_for_current_frame_callback = update_scene_for_current_frame_callback
        super().__init__(video_out_fpath, scale_factor, video_fps, parent, ControlPaneClass, GSClass, GVClass)

    def populate_scene(self):
        self.populate_scene_callback(self)

    def update_scene_for_current_frame(self):
        return self.update_scene_for_current_frame_callback(self)
