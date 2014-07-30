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
from pathlib import Path
from PyQt5 import Qt, uic

class ManualScorer(Qt.QDialog):
    class _ScoreRadioId(enum.IntEnum):
        ClearScore = 1
        SetScore0 = 2
        SetScore1 = 3
        SetScore2 = 4

    def __init__(self, imageDbFileName, modifyDbIfExists, parent):
        super().__init__(parent)

        if not modifyDbIfExists:
            imageDbFileName = Path(imageDbFileName)
            if imageDbFileName.exists():
                imageDbFileName.unlink()

        self._db = Qt.QtSql.QSqlDatabase.addDatabase('QSQLITE')
        if not self._db.isValid():
            raise RuntimeError('Qt appears to be built without SQLite support...')
        self._db.setDatabaseName(str(imageDbFileName))
        if not self._db.open():
            raise RuntimeError('Failed to open database file "{}".'.format(str(imageDbFileName)))

        self._ui = uic.loadUiType(os.path.join(os.path.dirname(__file__), 'manually_score_images.ui'))[0]()
        self._ui.setupUi(self)

        self._scoreRadioGroup = Qt.QButtonGroup(self)
        self._scoreRadioGroup.addButton(self._ui.radioNone, self._ScoreRadioId.ClearScore)
        self._scoreRadioGroup.addButton(self._ui.radio0, self._ScoreRadioId.SetScore0)
        self._scoreRadioGroup.addButton(self._ui.radio1, self._ScoreRadioId.SetScore1)
        self._scoreRadioGroup.addButton(self._ui.radio2, self._ScoreRadioId.SetScore2)

        self._ui.actionUp.triggered.connect(self._ui.prevGroupButton.animateClick)
        self._ui.actionDown.triggered.connect(self._ui.nextGroupButton.animateClick)
        self._ui.actionLeft.triggered.connect(self._ui.prevButton.animateClick)
        self._ui.actionRight.triggered.connect(self._ui.nextButton.animateClick)
        self._ui.actionBackspace.triggered.connect(self._ui.radioNone.animateClick)
        self._ui.action0.triggered.connect(self._ui.radio0.animateClick)
        self._ui.action1.triggered.connect(self._ui.radio1.animateClick)
        self._ui.action2.triggered.connect(self._ui.radio2.animateClick)

        self.addActions([self._ui.actionUp,
                         self._ui.actionDown,
                         self._ui.actionLeft,
                         self._ui.actionRight,
                         self._ui.actionBackspace,
                         self._ui.action0,
                         self._ui.action1,
                         self._ui.action2])


class ManualImageScorer(ManualScorer):
    def __init__(self, imageDbFileName, modifyDbIfExists=True, imageFileNames=None, subtractPrefix=None, parent=None):
        super().__init__(imageDbFileName, modifyDbIfExists, parent)

        self.removeAction(self._ui.actionUp)
        self.removeAction(self._ui.actionDown)
        self._ui.actionUp.deleteLater()
        self._ui.actionDown.deleteLater()
        del self._ui.actionUp
        del self._ui.actionDown

        self._ui.prevGroupButton.deleteLater()
        self._ui.nextGroupButton.deleteLater()
        del self._ui.prevGroupButton
        del self._ui.nextGroupButton

        # Todo: add list view, etc

class _ManualImageGroupScorerModel:

class ManualImageGroupScorer(ManualScorer):
    def __init__(self, imageDbFileName, modifyDbIfExists=True, imageFileNameGroups=None, subtractPrefix=None, parent=None):
        '''If subtractPrefix is specified, the leading component of image file names matching subtractPrefix are chopped off
        when saved to the DB.  For example, if subtractPrefix is '/home/userfoo', the file name field for the image at path
        '/home/userfoo/project_bar/run1/0102.png' will be 'project_bar/run1/0102.png'.'''
        super().__init__(imageDbFileName, modifyDbIfExists, parent)

        c = self._db.cursor()
        c.execute('CREATE TABLE IF NOT EXISTS groups (id INTEGER PRIMARY KEY, name TEXT UNIQUE'))
