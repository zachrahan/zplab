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
        
        self.wellsFPath = self.path / '{}_wells.csv'.format(self.name)
        if self.wellsFPath.exists():
            self.wells = pandas.read_csv(str(self.wellsFPath), escapechar='\\')
        self.dataFPath = self.path / '{}_data.csv'.format(self.name)
