from enum import IntEnum
import json
from PyQt5 import Qt
from pathlib import Path
from skimage import io as skio
for function in ('imread', 'imsave', 'imread_collection'):
    skio.use_plugin('freeimage', function)
import time

class AgingFluorescence(Qt.QObject):
    def __init__(self, root, out_dir, prefix):
        super().__init__()
        self.positionSetNames = ('reference', 'control', 'exp0', 'exp1', 'exp2')
        self.positionSets = [[] for n in self.positionSetNames]
        self.root = root
        self.get_more_positions_gt = None
        self.out_dir = Path(out_dir)
        self.prefix = prefix
        if not self.out_dir.exists():
            self.out_dir.mkdir(parents=True)
        self.positions_fpath = self.out_dir / (prefix + '_positions.json')
        if self.positions_fpath.exists():
            with open(str(self.positions_fpath), 'r') as f:
                psd = json.load(f)
                for name, set in psd.items():
                    self.positionSets[self.positionSetNames.index(name)] = set

    def get_more_positions(self):
        if hasattr(self, 'pos_get_dialog'):
            raise RuntimeError('get_more_positions() already in progress...')
        self.pos_get_dialog = Qt.QDialog()
        self.pos_get_dialog.setWindowTitle('Getting positions...')
        self.pos_get_dialog.setLayout(Qt.QVBoxLayout())
        self.pos_get_dialog.stop_button = Qt.QPushButton('stop getting positions')
        self.pos_get_dialog.layout().addWidget(self.pos_get_dialog.stop_button)
        self.pos_get_dialog.posSetLabel = Qt.QLabel('reference')
        self.pos_get_dialog.layout().addWidget(self.pos_get_dialog.posSetLabel)
        self.pos_get_dialog.stop_button.clicked.connect(self.stop_getting_positions)
        self.root.pedals.pedalUpChanged.connect(self.on_pedal_up)
        self.pos_get_dialog.show()

    def on_pedal_up(self, pedal, isUp):
        if not isUp:
            if pedal == 0:
                pos = (self.root.dm6000b.stageX.pos, self.root.dm6000b.stageY.pos, self.root.dm6000b.stageZ.pos)
                pl = self.positionSets[self.positionSetNames.index(self.pos_get_dialog.posSetLabel.text())]
                pl.append(pos)
            elif pedal == 1:
                n = self.positionSetNames.index(self.pos_get_dialog.posSetLabel.text())
                n += 1
                if n >= len(self.positionSetNames):
                    n = 0
                self.pos_get_dialog.posSetLabel.setText(self.positionSetNames[n])

    def stop_getting_positions(self):
        self.root.pedals.pedalUpChanged.disconnect(self.on_pedal_up)
        self.pos_get_dialog.close()
        del self.pos_get_dialog

    def save_positions(self):
        with open(str(self.positions_fpath), 'w') as f:
            json.dump({positionSetName : positions for positionSetName, positions in zip(self.positionSetNames, self.positionSets)}, f)

    def acquireForFilterSet(self, filterSetNumber, rw=None):
        imageCount = 4
        self.root.dm6000b.lamp.ilShutterOpened = True
        self.root.dm6000b.lamp.tlShutterOpened = True
        self.root.dm6000b.lamp.intensity = 255
        if filterSetNumber == 0:
            self.root.dm6000b.cubeTurret.cube = 'DFTr0'
        elif filterSetNumber == 1:
            self.root.dm6000b.cubeTurret.cube = 'CYmC0'
        else:
            raise ValueError('filterSetNumber must be 0 or 1')
        self.root.dm6000b.lamp.intensity = 255
        time.sleep(1)
        for positionSetName, positions in zip(self.positionSetNames, self.positionSets):
            for positionIndex, position in enumerate(positions):
                print('posindex: {}, position: {}'.format(positionIndex, position))
                self.root.dm6000b.stageX.pos, self.root.dm6000b.stageY.pos, self.root.dm6000b.stageZ.pos = position
                self.root.dm6000b.waitForReady()
                self.root.dm6000b.lamp.tlShutterOpened = True
                self.root.dm6000b.lamp.intensity = 255
                self.root.camera._camera.AT_Flush()
                buffers = [self.root.camera.makeAcquisitionBuffer() for i in range(imageCount)]
                self.root.camera.shutter = self.root.camera.Shutter.Rolling
                self.root.camera.triggerMode = self.root.camera.TriggerMode.Software
                self.root.camera.cycleMode = self.root.camera.CycleMode.Fixed
                # 10ms brightfield exposure time
                self.root.camera.exposureTime = 0.010
                bfAcquisitionTime = self.root.camera.exposureTime + 0.02
                self.root.camera.frameCount = imageCount
                for buffer in buffers:
                    self.root.camera._camera.AT_QueueBuffer(buffer)
                self.root.camera._camera.AT_Command(self.root.camera.Feature.AcquisitionStart)
                # Wait for TL shutter to open
                time.sleep(1)
                self.root.brightfieldLed.enabled = True
                self.root.brightfieldLed.power = 108
                time.sleep(0.2)
                self.root.camera.commandSoftwareTrigger()
                time.sleep(bfAcquisitionTime)
                self.root.brightfieldLed.enabled = False
                self.root.dm6000b.lamp.tlShutterOpened = False
                self.root.dm6000b.lamp.intensity = 255
                # Wait for TL shutter to close
                time.sleep(1)
                # 50ms fluorescence exposure time
                self.root.camera.exposureTime = 0.050
                fluoAcquisitionTime = self.root.camera.exposureTime + 0.03
                if filterSetNumber == 0:
                    self.root.lumencor.UVEnabled = True
                    self.root.lumencor.UVPower = 4 if positionSetName == "reference" else 255
                    time.sleep(0.08)
                    self.root.camera.commandSoftwareTrigger()
                    time.sleep(fluoAcquisitionTime)
                    self.root.lumencor.UVEnabled = False
                    self.root.lumencor.cyanEnabled = True
                    self.root.lumencor.cyanPower = 255
                    time.sleep(0.08)
                    self.root.camera.commandSoftwareTrigger()
                    time.sleep(fluoAcquisitionTime)
                    self.root.lumencor.cyanEnabled = False
                    self.root.lumencor.greenEnabled = True
                    self.root.lumencor.greenPower = 255
                    time.sleep(0.08)
                    self.root.camera.commandSoftwareTrigger()
                    time.sleep(fluoAcquisitionTime)
                    self.root.lumencor.greenEnabled = False
                    self.root.lumencor.disable()
                    names = ['bf-DFTr', 'DAPI', 'FITC', 'TRITC']
                elif filterSetNumber == 1:
                    self.root.lumencor.blueEnabled = True
                    self.root.lumencor.bluePower = 255
                    time.sleep(0.08)
                    self.root.camera.commandSoftwareTrigger()
                    time.sleep(fluoAcquisitionTime)
                    self.root.lumencor.blueEnabled = False
                    self.root.lumencor.tealEnabled = True
                    self.root.lumencor.tealPower = 255
                    time.sleep(0.08)
                    self.root.camera.commandSoftwareTrigger()
                    time.sleep(fluoAcquisitionTime)
                    self.root.lumencor.tealEnabled = False
                    self.root.lumencor.greenEnabled = True
                    self.root.lumencor.greenPower = 255
                    time.sleep(0.08)
                    self.root.camera.commandSoftwareTrigger()
                    time.sleep(fluoAcquisitionTime)
                    self.root.lumencor.greenEnabled = False
                    self.root.lumencor.disable()
                    names = ['bf-CYmC', 'CFP', 'YFP', 'mCherry']
                for i in range(imageCount):
                    self.root.camera._camera.AT_WaitBuffer(1000)
                self.root.camera._camera.AT_Command(self.root.camera.Feature.AcquisitionStop)
                for i in range(imageCount):
                    imFP = self.out_dir / '{}_{}_{:04}_{}.png'.format(self.prefix, positionSetName, positionIndex, names[i])
                    if rw is not None:
                        rw.showImage(buffers[i])
                    skio.imsave(str(imFP), buffers[i][:2160,:2560])
