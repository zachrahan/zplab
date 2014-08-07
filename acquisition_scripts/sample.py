import json
from PyQt5 import Qt
import pandas
from pathlib import Path

class Experiment(Qt.QObject):
    def __init__(self, deviceTreeRoot, experimentName, experimentDataDirectory, parent=None):
        super().__init__(parent)
        self.root = deviceTreeRoot
        self.name = experimentName
        self.path = Path(experimentDataDirectory)
        if not self.path.exists():
            self.path.mkdir(parents=True)
        self.runTimer = Qt.QTimer(self)
        # The index of the most recently completed or currently executing run
        self.runIndex = -1

        self.storeFPath = self.path / '{}__wells_and_data.h5'.format(self.name)
        self.store = pandas.HDFStore(str(self.storeFPath))

        self.lastWellIndex = -1
        if 'wells' in self.store:
            self.lastWellIndex = self.store.get_storer('wells').nrows - 1

        self.lastRunIndex = -1
        if 'data' in self.store:
            self.lastRunIndex = self.store.get_storer('data').nrows - 1

        self.configFPath = self.path / '{}__config.json'.format(self.name)
        if self.configFPath.exists():
            with self.configFPath.
        else:
            self.config = {'interval_in_milliseconds'

    def storeWell(self, x, y, z):
        self.lastWellIndex += 1
        well = {'well':self.lastWellIndex, 'x':x, 'y':y, 'z':z}
        self.store.append('wells', pandas.DataFrame((well,)), format='t')

    def storeDataRow(self, imageFPath, x, y, z, fmName, fmValue, type_):
        self.lastRunIndex += 1
        self.store.append('data', pandas.DataFrame)
