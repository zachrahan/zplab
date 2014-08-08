import asyncio
import json
from PyQt5 import Qt
import pandas
from pathlib import Path
import quamash
from skimage import io as skio
for function in ('imread', 'imsave', 'imread_collection'):
    skio.use_plugin('freeimage', function)
import time

class _AddWellsDialog(Qt.QDialog):
    doneSignal = Qt.pyqtSignal()

    def __init__(self, experiment, prefix):
        super().__init__()
        self.experiment = experiment
        self.prefix = prefix
        self.setAttribute(Qt.Qt.WA_DeleteOnClose, True)
        self.setWindowTitle('well adder control')
        self.setLayout(Qt.QHBoxLayout())
        self.nextWellButton = Qt.QPushButton('Save Well')
        self.doneButton = Qt.QPushButton('Done')
        self.layout().addWidget(self.nextWellButton)
        self.layout().addWidget(self.doneButton)
        self.nextWellButton.clicked.connect(self.nextWellSlot)
        self.doneButton.clicked.connect(self.doneClickedSlot)

    def nextWellSlot(self):
        self.experiment.wells.append({'well':'{}_{:04}'.format(self.prefix, len(self.experiment.wells)),
                                      'x':self.experiment.root.dm6000b.stageX.pos,
                                      'y':self.experiment.root.dm6000b.stageY.pos,
                                      'z':self.experiment.root.dm6000b.stageZ.pos})

    def doneClickedSlot(self):
        self.doneSignal.emit()
        self.close()

class Experiment(Qt.QObject):
    def __init__(self, deviceTreeRoot, experimentName, experimentDataDirectory, parent=None):
        super().__init__(parent)

        self.root = deviceTreeRoot
        self.name = experimentName
        self.path = Path(experimentDataDirectory)
        if not self.path.exists():
            self.path.mkdir(parents=True)

        self.runTimer = Qt.QTimer(self)
        self.runTimer.timeout.connect(self._executeRun)

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
        self.runTime = 0
        if self.checkpointFPath.exists():
            with self.checkpointFPath.open() as checkpointF:
                checkpoint = json.load(checkpointF)
            self.runIndex = checkpoint['runIndex']
            self.runTime = checkpoint['runTime']

    def _writeConfig(self):
        with self.configSwapTempFPath.open('w') as configSwapTempF:
            config = {'interval':self.interval,
                      'wells':self.wells}
            json.dump(config, configSwapTempF)
        self.configSwapTempFPath.replace(self.configFPath)

    def _writeCheckpoint(self):
        with self.checkpointSwapTempFPath.open('w') as checkpointSwapTempF:
            checkpoint = {'runIndex':self.runIndex,
                          'runTime':self.runTime}
            json.dump(checkpoint, checkpointSwapTempF)
        self.checkpointSwapTempFPath.replace(self.checkpointFPath)

    def addWells(self, prefix):
        addWellsDialog = _AddWellsDialog(self, prefix)
        addWellsDialog.show()
        self._waitForSignal(addWellsDialog.doneSignal)

    def start(self, interval):
        self.interval = interval
        self._writeConfig()
        self._writeCheckpoint()
        self.resume()

    def resume(self):
        if self.interval <= 0:
            raise ValueError('interval must be positive.')
        if len(self.wells) == 0:
            raise RuntimeError('Please add some wells before starting the experiment.')
        delta = time.time() - self.runTime
        if delta > self.interval:
            self._executeRun()
        else:
            self.runTimer.setSingleShot(True)
            self.runTimer.start(delta * 1000)

    def _executeRun(self):
        if self.runTimer.isSingleShot():
            self.runTimer.setSingleShot(False)
            self.runTimer.start(self.interval * 1000)
        elif not self.runTimer.isActive():
            self.runTimer.start(self.interval * 1000)
        self.runTime = time.time()
        self.runIndex += 1
        self._writeCheckpoint()
        for well in self.wells:
            print('run: {} well: {}'.format(self.runIndex, well['well']))
            self.root.lumencor.disable()
            self.root.brightfieldLed.enabled = True
            self.root.brightfieldLed.power = 255
            runWellPath = self.path / 'well_{}'.format(well['well']) / 'run_{:04}'.format(self.runIndex)
            if not runWellPath.exists():
                runWellPath.mkdir(parents=True)
            metaDataFPath = runWellPath / '{}_{}__meta_data.json'.format(self.name, well['well'])
            metaData = {}
            self.root.dm6000b.stageX.pos, self.root.dm6000b.stageY.pos = well['x'], well['y']
            self.root.dm6000b.waitForReady()
            self.root.camera.exposureTime = 0.01
            self.root.autoFocuser.startAutoFocus(24.75, 25.75, 10)
            self.root.waitForReady()
            Qt.QApplication.processEvents()
            self.root.camera._camera.AT_Flush()
            buffers = [self.root.camera.makeAcquisitionBuffer() for i in range(4)]
            self.root.camera.shutter = self.root.camera.Shutter.Rolling
            self.root.camera.triggerMode = self.root.camera.TriggerMode.Software
            self.root.camera.cycleMode = self.root.camera.CycleMode.Fixed
            self.root.camera.frameCount = 4
#           map(self.root.camera._camera.AT_QueueBuffer, buffers)
            for buffer in buffers:
                self.root.camera._camera.AT_QueueBuffer(buffer)
            self.root.camera._camera.AT_Command(self.root.camera.Feature.AcquisitionStart)
            self.root.camera.commandSoftwareTrigger()
            time.sleep(0.020)
            self.root.brightfieldLed.enabled = False
            self.root.lumencor.cyanEnabled = True
            self.root.lumencor.cyanPower = 255
            time.sleep(0.008)
            self.root.camera.commandSoftwareTrigger()
            time.sleep(0.020)
            self.root.lumencor.blueEnabled = True
            self.root.lumencor.bluePower = 255
            self.root.lumencor.UVEnabled = True
            self.root.lumencor.UVPower = 255
            time.sleep(2)
            self.root.lumencor.cyanEnabled = False
            self.root.lumencor.blueEnabled = False
            self.root.lumencor.UVEnabled = False
            self.root.brightfieldLed.enabled = True
            time.sleep(0.008)
            self.root.camera.commandSoftwareTrigger()
            time.sleep(1)
            self.root.camera.commandSoftwareTrigger()
            time.sleep(0.020)
            self.root.brightfieldLed.enabled = False
            for i in range(4):
                print(i)
                self.root.camera._camera.AT_WaitBuffer(1000)
            self.root.camera._camera.AT_Command(self.root.camera.Feature.AcquisitionStop)
            metaData['timestamp'] = time.time()
            metaData['temperature'] = self.root.incubator.get_current_temp()
            metaData['exposure'] = self.root.camera.exposureTime
            metaData['x'] = self.root.dm6000b.stageX.pos
            metaData['y'] = self.root.dm6000b.stageY.pos
            z = self.root.autoFocuser._results[0][0]
#           while z != z:
            print('Z: {}'.format(z))
#               z = self.root.dm6000b.stageZ.pos
            metaData['z'] = self.root.autoFocuser._results[0][0]
            metaData['mag'] = self.root.dm6000b.objectiveTurret.mag

            imFP = runWellPath / 'bf_image.png'
            metaData['bf_image'] = str(imFP)
            self.root.autoFocuser.rw.showImage(buffers[0])
            skio.imsave(str(imFP), buffers[0])

            imFP = runWellPath / 'fluo_image.png'
            metaData['fluo_image'] = str(imFP)
            self.root.autoFocuser.rw.showImage(buffers[1])
            skio.imsave(str(imFP), buffers[1])

            imFP = runWellPath / 'bf_agitated0_image.png'
            metaData['bf_agitated0_image'] = str(imFP)
            self.root.autoFocuser.rw.showImage(buffers[2])
            skio.imsave(str(imFP), buffers[2])

            imFP = runWellPath / 'bf_agitated1_image.png'
            metaData['bf_agitated1_image'] = str(imFP)
            self.root.autoFocuser.rw.showImage(buffers[3])
            skio.imsave(str(imFP), buffers[3])

            with metaDataFPath.open('w') as metaDataF:
                json.dump(metaData, metaDataF)

    def _waitForSignal(self, signal):
        with quamash.QEventLoop(app=Qt.QApplication.instance()) as loop:
            loop.run_until_complete(self._waitForSignalCoroutine(signal))

    @asyncio.coroutine
    def _waitForSignalCoroutine(self, signal):
        def onSignal():
            fut.set_result(True)
        fut = asyncio.Future()
        signal.connect(onSignal)
        yield from fut
