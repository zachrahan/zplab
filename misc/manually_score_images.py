# The MIT License (MIT)
#
# Copyright (c) 2014 WUSTL ZPLAB
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
# Authors: Erik Hvatum

import enum
import os
from PyQt5 import Qt, uic
import sqlite3

class ManualImageScorer(Qt.QDialog):
    class _ScoreRadioId(enum.IntEnum):
        ClearScore = 1
        SetScore0 = 2
        SetScore1 = 3
        SetScore2 = 4

    def __init__(self, imageRootPath, imageDbFileName, imageFileNames, parent=None):
        super().__init__(parent)

        self.ui = uic.loadUiType(os.path.join(os.path.dirname(__file__), 'manually_score_images.ui'))[0]()
        self.ui.setupUi(self)

        self._scoreRadioGroup = Qt.QButtonGroup(self)
        self._scoreRadioGroup.addButton(self.ui.radioNone, self._ScoreRadioId.ClearScore)
        self._scoreRadioGroup.addButton(self.ui.radio0, self._ScoreRadioId.SetScore0)
        self._scoreRadioGroup.addButton(self.ui.radio1, self._ScoreRadioId.SetScore1)
        self._scoreRadioGroup.addButton(self.ui.radio2, self._ScoreRadioId.SetScore2)

        self.ui.actionLeft.triggered.connect(self.ui.prevButton.animateClick)
        self.ui.actionRight.triggered.connect(self.ui.nextButton.animateClick)
        self.ui.actionBackspace.triggered.connect(self.ui.radioNone.animateClick)
        self.ui.action0.triggered.connect(self.ui.radio0.animateClick)
        self.ui.action1.triggered.connect(self.ui.radio1.animateClick)
        self.ui.action2.triggered.connect(self.ui.radio2.animateClick)

        self.addActions([self.ui.actionLeft,
                         self.ui.actionRight,
                         self.ui.actionBackspace,
                         self.ui.action0,
                         self.ui.action1,
                         self.ui.action2])


