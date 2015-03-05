# The MIT License (MIT)
#
# Copyright (c) 2014-2015 WUSTL ZPLAB
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

import concurrent.futures
import csv
import enum
import pandas
from pathlib import Path
import pickle
from PyQt5 import Qt, uic
import numpy
import os
import re
import skimage.io as skio
import zmq

class ScoreableImage:
    def __init__(self, fileName, score=None):
        self.fileName = fileName
        self.score = score
    def __repr__(self):
        return 'ScoreableImage({}, {})'.format(self.fileName, self.score)

class MigsFmRow:
    def __init__(self, fileName=None, well=None, mag=None, run=None, xPos=None, yPos=None, zPos=None, temperature=None, score=None, fmName=None, fmValue=None):
        if fileName is not None:
            self.fileName = Path(fileName)
        else:
            self.fileName = None

        if self.fileName is not None and well is None:
            match = re.match('''^\/mnt\/scopearray\/autofocus\/weekend\/(\d\d)_([^_]+)_([^_]+)_[^/]+/(5x|10x)/(\d+)/([^_]+)_(\d+\.?\d*)\.png$''', str(self.fileName))
            if match is None:
                raise RuntimeError('regex match failure')
            self.well = int(match.group(1))
            self.mag = match.group(4)
            self.run = int(match.group(5))
            self.xPos = int(match.group(2))
            self.yPos = int(match.group(3))
            self.zPos = int(match.group(6))
            self.temperature = float(match.group(7))
        else:
            self.well = well
            self.mag = mag
            self.run = run
            self.xPos = xPos
            self.yPos = yPos
            self.zPos = zPos
            self.temperature = temperature
        self.score = score
        self.fmName = fmName
        self.fmValue = fmValue
        if self.fmValue is not None:
            self.fmValue = float(self.fmValue)
    def __repr__(self):
        return 'MigsFmRow(fileName={}, well={}, mag={}, run={}, xPos={}, yPos={}, zPos={}, temperature={}, score={}, fmName={}, fmValue={})'.format(str(self.fileName),
                                                                                                                                                    self.well,
                                                                                                                                                    self.mag,
                                                                                                                                                    self.run,
                                                                                                                                                    self.xPos,
                                                                                                                                                    self.yPos,
                                                                                                                                                    self.zPos,
                                                                                                                                                    self.temperature,
                                                                                                                                                    self.score,
                                                                                                                                                    self.fmName,
                                                                                                                                                    self.fmValue)
    def rawCols():
        return ['Well', 'Mag', 'Run', 'xPos', 'yPos', 'zPos', 'Score', 'FocusMeasureName', 'FocusMeasureValue', 'Temperature', 'FileName']
    def rawRow(self):
        return [self.well, self.mag, self.run, self.xPos, self.yPos, self.zPos, self.score, self.fmName, self.fmValue, self.temperature, self.fileName]

def readMigsFromConsoleDumpCsvAndGroupsPickle(csvFileName, migsdatFileName):
    with open(str(migsdatFileName), 'rb') as f:
        migsdat = pickle.load(f)
    imageFnToScores = {}
    for group, scoreableImages in migsdat.items():
        for scoreableImage in scoreableImages:
            imageFnToScores[scoreableImage.fileName] = scoreableImage.score
    migsFmTable = []
    with open(str(csvFileName), 'r') as f:
        for row in csv.reader(f, delimiter=','):
            if len(row) == 3 and re.match('''^\/mnt\/scopearray\/autofocus\/weekend\/(\d\d)_([^_]+)_([^_]+)_[^/]+/(5x|10x)/(\d+)/([^_]+)_(\d+\.?\d*)\.png$''', row[0]) is not None:
                imageFileName = Path(row[0])
                r = MigsFmRow(fileName=imageFileName, fmName=row[1], fmValue=row[2], score=imageFnToScores[imageFileName])
                migsFmTable.append(r.rawRow())
    return pandas.DataFrame(columns=MigsFmRow.rawCols(), data=migsFmTable)

class ManualScorer(Qt.QDialog):
    class _ScoreRadioId(enum.IntEnum):
        ClearScore = 1
        SetScore0 = 2
        SetScore1 = 3
        SetScore2 = 4

    _radioIdToScore = {_ScoreRadioId.ClearScore : None,
                       _ScoreRadioId.SetScore0 : 0,
                       _ScoreRadioId.SetScore1 : 1,
                       _ScoreRadioId.SetScore2 : 2}

    def __init__(self, risWidget, dict_, parent):
        super().__init__(parent)

        self._rw = risWidget
        self._db = dict_

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
    '''imageDict format: {pathlib.Path object referring to image : score (None if no score assigned)}'''
    _ImageFPathRole = 42
    _Forward = 0
    _Backward = 1

    def __init__(self, risWidget, imageDict, parent=None):
        super().__init__(risWidget, imageDict, parent)

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

        self._ui.tableWidget.setColumnCount(2)

        self._db = imageDict
        self._imageFPaths = sorted(list(self._db.keys()))

        self._ui.tableWidget.setRowCount(len(self._db))
        self._ui.tableWidget.setHorizontalHeaderLabels(['Image', 'Rating'])
        for rowIndex, imageFPath in enumerate(self._imageFPaths):
            imageScore = self._db[imageFPath]
            imageItem = Qt.QTableWidgetItem(str(imageFPath));
            imageItem.setData(self._ImageFPathRole, Qt.QVariant(imageFPath))
            self._ui.tableWidget.setItem(rowIndex, 0, imageItem)
            self._ui.tableWidget.setItem(rowIndex, 1, Qt.QTableWidgetItem('None' if imageScore is None else str(imageScore)))

        self._curImageFPath = None
        self._inRefreshScoreButtons = False

        self._readAheadImageFPath = None
        self._readAheadExecutor = concurrent.futures.ThreadPoolExecutor(2)
        self._readAheadFuture = None

        self._ui.tableWidget.currentItemChanged.connect(self._listWidgetSelectionChange)
        self._scoreRadioGroup.buttonClicked[int].connect(self._scoreButtonClicked)
        self._ui.prevButton.clicked.connect(lambda: self._stepImage(self._Backward))
        self._ui.nextButton.clicked.connect(lambda: self._stepImage(self._Forward))

        self._ui.tableWidget.setCurrentItem(self._ui.tableWidget.item(0, 0))

    def _listWidgetSelectionChange(self, curItem, prevItem):
        imageItem = self._ui.tableWidget.item(curItem.row(), 0)
        self._curImageFPath = imageItem.data(self._ImageFPathRole)
        self._refreshScoreButtons()
        if self._readAheadFuture is not None and self._curImageFPath == self._readAheadImageFPath:
            image = self._readAheadFuture.result()
        else:
            image = self._getImage(self._curImageFPath)
        if image is not None:
            if image.dtype == numpy.float32:
                image = (image * 65535).astype(numpy.uint16)
            self._rw.showImage(image)

    def _refreshScoreButtons(self):
        self._inRefreshScoreButtons = True
        score = self._db[self._curImageFPath]
        if score is None:
            self._ui.radioNone.click()
        elif score is 0:
            self._ui.radio0.click()
        elif score is 1:
            self._ui.radio1.click()
        elif score is 2:
            self._ui.radio2.click()
        else:
            self._inRefreshScoreButtons = False
            raise RuntimeError('Bad value for image score.')
        self._inRefreshScoreButtons = False

    def _scoreButtonClicked(self, radioId):
        if not self._inRefreshScoreButtons:
            self._setScore(self._radioIdToScore[radioId])
            self._ui.nextButton.animateClick()

    def _setScore(self, score):
        '''Set current image score.'''
        if score != self._db[self._curImageFPath]:
            self._db[self._curImageFPath] = score
            self._ui.tableWidget.item(self._ui.tableWidget.currentRow(), 1).setText('None' if score is None else str(score))

    def _stepImage(self, direction):
        curRow = self._ui.tableWidget.currentRow()
        newRow = None
        oneAfter = None
        
        if direction == self._Forward:
            if curRow + 1 < self._ui.tableWidget.rowCount():
                newRow = curRow + 1
            if curRow + 2 < self._ui.tableWidget.rowCount():
                oneAfter = curRow + 2
        elif direction == self._Backward:
            if curRow > 0:
                newRow = curRow - 1
            if curRow - 1 > 0:
                oneAfter = curRow - 2
        
        if newRow is not None:
            self._ui.tableWidget.setCurrentItem(self._ui.tableWidget.item(newRow, 0))

        if oneAfter is not None:
            if self._readAheadFuture is not None and self._readAheadFuture.running():
                concurrent.futures.wait((self._readAheadFuture, ))
            self._readAheadImageFPath = self._ui.tableWidget.item(oneAfter, 0).data(self._ImageFPathRole)
            self._readAheadFuture = self._readAheadExecutor.submit(self._getImage, self._readAheadImageFPath)

    def _getImage(self, imageFPath):
        return skio.imread(str(imageFPath))

    @property
    def imageDict(self):
        return self._db

class RemoteManualImageScorer(ManualImageScorer):
    def __init__(self, risWidget, imageDict, imageServerURI, zmqContext, parent=None):
        self._zc = zmqContext
        self._reqToServer = self._zc.socket(zmq.REQ)
        self._reqToServer.connect(imageServerURI)
        super().__init__(risWidget, imageDict, parent)

    def _recv_array(self, flags=0, copy=False, track=True):
        """recv a numpy array"""
        md = self._reqToServer.recv_pyobj(flags=flags)
        msg = self._reqToServer.recv(flags=flags, copy=copy, track=track)
        buf = memoryview(msg)
        A = numpy.frombuffer(buf, dtype=md['dtype'])
        return A.reshape(md['shape'])

    def _getImage(self, imageFPath):
        self._reqToServer.send_pyobj({'command' : 'send image array',
                                      'imageFPath' : imageFPath})
        md = self._reqToServer.recv_pyobj()
        if md['status'] != 'ok':
            print('Failed to retrieve "{}" from image server.'.format(str(imageFPath)))
        else:
            image = self._recv_array()
            return image

    def sendImageServerQuitRequest(self):
        self._reqToServer.send_pyobj({'command' : 'quit'})
        if self._reqToServer.recv_pyobj()['status'] == 'ok':
            print('server accepted quit command')
        else:
            print('server did NOT accept quit command')

class ImageServer:
    def __init__(self, zmqContext, imageServerURIs):
        self._zc = zmqContext
        self._repToClient = self._zc.socket(zmq.REP)
        if type(imageServerURIs) is str:
            self._repToClient.bind(imageServerURIs)
        else:
            for imageServerURI in imageServerURIs:
                self._repToClient.bind(imageServerURI)

    def _send_array(self, A, flags=0, copy=False, track=True):
        """send a numpy array with metadata"""
        md = dict(
            dtype = str(A.dtype),
            shape = A.shape,
        )
        self._repToClient.send_pyobj(md, flags|zmq.SNDMORE)
        self._repToClient.send(A, flags, copy=copy, track=track)

    def run(self):
        while True:
            md = self._repToClient.recv_pyobj()
            if md['command'] == 'quit':
                self._repToClient.send_pyobj({'status' : 'ok'})
                print('received quit request...')
                break
            elif md['command'] == 'send image array':
                image = skio.imread(str(md['imageFPath']))
                self._repToClient.send_pyobj({'status' : 'ok'}, zmq.SNDMORE)
                self._send_array(image)

class ManualImageGroupScorer(ManualScorer):
    '''groupDict format: {'group name' : [ScoreableImage, ScoreableImage, ...]}'''
    _GroupIndexRole = 42
    _FileIndexRole = 43
    _RowIndexRole = 44
    _Forward = 0
    _Backward = 1

    def __init__(self, risWidget, groupDict, parent=None):
        super().__init__(risWidget, groupDict, parent)

        imageCount = sum((len(images) for images in self._db.values()))
        self._ui.tableWidget.setRowCount(imageCount)
        self._ui.tableWidget.setHorizontalHeaderLabels(['Group', 'File name', 'Rating'])

        rowIndex = 0
        self._groupNames = sorted(list(self._db.keys()))
        for groupIndex, groupName in enumerate(self._groupNames):
            images = self._db[groupName]
            for imageIndex, image in enumerate(images):
                groupItem = Qt.QTableWidgetItem(groupName)
                groupItem.setData(self._GroupIndexRole, Qt.QVariant(groupIndex))
                groupItem.setData(self._FileIndexRole, Qt.QVariant(imageIndex))
                groupItem.setData(self._RowIndexRole, Qt.QVariant(rowIndex))
                self._ui.tableWidget.setItem(rowIndex, 0, groupItem)
                self._ui.tableWidget.setItem(rowIndex, 1, Qt.QTableWidgetItem(str(image.fileName)))
                self._ui.tableWidget.setItem(rowIndex, 2, Qt.QTableWidgetItem('None' if image.score is None else str(image.score)))
                rowIndex += 1

        self._curGroupName = None
        self._curGroupIndex = None
        self._curGroupImages = None
        self._curImage = None
        self._curImageIndex = None
        self._curRowIndex = None

        self._inRefreshScoreButtons = False

        self._ui.tableWidget.currentItemChanged.connect(self._listWidgetSelectionChange)
        self._scoreRadioGroup.buttonClicked[int].connect(self._scoreButtonClicked)
        self._ui.prevGroupButton.clicked.connect(lambda: self._stepGroup(self._Backward))
        self._ui.nextGroupButton.clicked.connect(lambda: self._stepGroup(self._Forward))
        self._ui.prevButton.clicked.connect(lambda: self._stepImage(self._Backward))
        self._ui.nextButton.clicked.connect(lambda: self._stepImage(self._Forward))

        self._ui.tableWidget.setCurrentItem(self._ui.tableWidget.item(0, 0))

    def _listWidgetSelectionChange(self, curItem, prevItem):
        groupItem = self._ui.tableWidget.item(curItem.row(), 0)
        self._curGroupIndex = groupItem.data(self._GroupIndexRole)
        self._curGroupName = groupItem.text()
        self._curGroupImages = self._db[self._curGroupName]
        self._curImageIndex = groupItem.data(self._FileIndexRole)
        self._curImage = self._curGroupImages[self._curImageIndex]
        self._curRowIndex = groupItem.data(self._RowIndexRole)
        self._refreshScoreButtons()
        image = skio.imread(str(self._curImage.fileName))
        if image.dtype == numpy.float32:
            image = (image * 65535).astype(numpy.uint16)
        self._rw.showImage(image)

    def _refreshScoreButtons(self):
        self._inRefreshScoreButtons = True
        score = self._curImage.score
        if score is None:
            self._ui.radioNone.click()
        elif score is 0:
            self._ui.radio0.click()
        elif score is 1:
            self._ui.radio1.click()
        elif score is 2:
            self._ui.radio2.click()
        else:
            self._inRefreshScoreButtons = False
            raise RuntimeError('Bad value for image score.')
        self._inRefreshScoreButtons = False

    def _scoreButtonClicked(self, radioId):
        if not self._inRefreshScoreButtons:
            self._setScore(self._radioIdToScore[radioId])
            self._ui.nextButton.animateClick()

    def _setScore(self, score):
        '''Set current image score.'''
        if score != self._curImage.score:
            self._curImage.score = score
            self._ui.tableWidget.item(self._curRowIndex, 2).setText('None' if score is None else str(score))

    def _stepImage(self, direction):
        newRow = None
        if direction == self._Forward:
            if self._curRowIndex + 1 < self._ui.tableWidget.rowCount():
                newRow = self._curRowIndex + 1
        elif direction == self._Backward:
            if self._curRowIndex > 0:
                newRow = self._curRowIndex - 1
        
        if newRow is not None:
            self._ui.tableWidget.setCurrentItem(self._ui.tableWidget.item(newRow, 0))

    def _stepGroup(self, direction):
        newRow = None
        if direction == self._Forward:
            if self._curGroupIndex + 1 < len(self._db):
                newRow = self._curRowIndex + len(self._curGroupImages) - self._curImageIndex
        elif direction == self._Backward:
            if self._curGroupIndex > 0:
                newGroup = self._curGroupIndex - 1
                newRow = self._curRowIndex - len(self._curGroupImages) + self._curImageIndex - 1

        if newRow is not None:
            self._ui.tableWidget.setCurrentItem(self._ui.tableWidget.item(newRow, 0))

def makeInitialWeekendImagesScorer(risWidget, basePath):
    import re
    groups = {}
    basePath = Path(basePath)

    for well in basePath.glob('*'):
        if well.is_dir():
            wellIdx = well.name
            match = re.search('^(\d\d)', wellIdx)
            if match is not None:
                wellIdx = match.group(1)
                for mag in well.glob('*'):
                    magName = mag.name
                    if mag.is_dir() and magName in ['5x', '10x']:
                        for run in mag.glob('*'):
                            runNum = run.name
                            if run.is_dir() and re.match('\d+', runNum):
                                runNum = int(runNum)
                                images = [ScoreableImage(imageFile) for imageFile in run.glob('*.png')]
                                group = '{}/{}/{:02}'.format(wellIdx, magName, runNum)
                                groups[group] = images

    migs = ManualImageGroupScorer(risWidget, groups)
    migs.show()
    return groups, migs

def makeResumeWeekendImagesScorer(risWidget, groups):
    migs = ManualImageGroupScorer(risWidget, groups)
    migs.show()
    return migs
