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

        self.configFPath = self.path / '{}__config.json'.format(self.name)
        self.configSwapTempFPath = self.path / '{}__config.json._'.format(self.name)

        self.checkpointFPath = self.path / '{}__checkpoint.json'.format(self.name)
        self.checkpointSwapTempFPath = self.path / '{}__checkpoint.json._'.format(self.name)

        self.wells = []
        self.interval = None
        if self.configFPath.exists():
            with self.configFPath.open() as configF:
                config = json.load(configF)
            self.interval = config['interval']
            self.wells = config['wells']

        # The index of the most recently completed or currently executing run
        self.runIndex = -1
        # The start time of the most recently completed or currently executing run
        self.runTime = None
        if self.checkpointFPath.exists():
            with self.checkpointFPath.open() as checkpointF:
                checkpoint = json.load(checkpointF)
            self.runIndex = checkpoint['runIndex']
            self.runTime = checkpoint['runTime']

    def writeConfig(self):
        with self.configSwapTempFPath.open('w') as configSwapTempF:
            config = {'interval':self.interval,
                      'wells':self.wells}
            json.dump(configSwapTempF, config)
        self.configSwapTempFPath.replace(self.configFPath)

    def writeCheckpoint(self):
        with self.checkpointSwapTempFPath.open('w') as checkpointSwapTempF:
            checkpoint = {'runIndex':self.runIndex,
                          'runTime':self.runTime}
            json.dump(checkpointSwapTempF, checkpoint)
        self.checkpointSwapTempFPath.replace(self.checkpointFPath)

    def addWells(self):
        from acquisition.pedals.pedal import WaitPedal
        wp = WaitPedal('/dev/ttyACM2')
            try:
                while True:
                    root.dm6000b.objectiveTurret.position = 1
                    wp.wait('high')
                    root.dm6000b.objectiveTurret.position = 2
                    wp.wait('low')
                    wp.wait('high')
                    
                    poss.append(getstage())
                    wp.wait('low')
            except KeyboardInterrupt:
                return poss

    def start(self, interval):
        pass

    def resume(self):
        pass
