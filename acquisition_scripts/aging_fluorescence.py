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
        self.root = root
        self.positions_control = []
        self.positions_exp = []
        self.get_more_positions_gt = None
        self.out_dir = Path(out_dir)
        self.prefix = prefix
        if not self.out_dir.exists():
            self.out_dir.mkdir(parents=True)
        self.positions_fpath = self.out_dir / (prefix + '_positions.json')
        if self.positions_fpath.exists():
            with open(str(self.positions_fpath), 'r') as f:
                self.positions_control, self.positions_exp = json.load(f)

    def get_more_positions(self):
        if hasattr(self, 'pos_get_dialog'):
            raise RuntimeError('get_more_positions() already in progress...')
        self.pos_get_dialog = Qt.QDialog()
        self.pos_get_dialog.setWindowTitle('Getting positions...')
        self.pos_get_dialog.setLayout(Qt.QVBoxLayout())
        self.pos_get_dialog.stop_button = Qt.QPushButton('stop getting positions')
        self.pos_get_dialog.layout().addWidget(self.pos_get_dialog.stop_button)
        self.pos_get_dialog.posSetLabel = Qt.QLabel('control')
        self.pos_get_dialog.layout().addWidget(self.pos_get_dialog.posSetLabel)
        self.pos_get_dialog.stop_button.clicked.connect(self.stop_getting_positions)
        self.root.pedals.pedalUpChanged.connect(self.on_pedal_up)
        self.pos_get_dialog.show()

    def on_pedal_up(self, pedal, isUp):
        if not isUp:
            if pedal == 0:
                pos = (self.root.dm6000b.stageX.pos, self.root.dm6000b.stageY.pos, self.root.dm6000b.stageZ.pos)
                pl = self.positions_control if self.pos_get_dialog.posSetLabel.text() == 'control' else self.positions_exp
                pl.append(pos)
            elif pedal == 1:
                self.pos_get_dialog.posSetLabel.setText('control' if self.pos_get_dialog.posSetLabel.text() == 'exp' else 'exp')

    def stop_getting_positions(self):
        self.root.pedals.pedalUpChanged.disconnect(self.on_pedal_up)
        self.pos_get_dialog.close()
        del self.pos_get_dialog

    def save_positions(self):
        with open(str(self.positions_fpath), 'w') as f:
            json.dump((self.positions_control, self.positions_exp), f)

    def acquireForFilterSet(self, filterSetNumber, rw=None):
        imageCount = 4
        self.root.dm6000b.lamp.ilShutterOpened = True
        self.root.dm6000b.lamp.tlShutterOpened = True
        if filterSetNumber == 0:
            self.root.dm6000b.cubeTurret.cube = 'DFTr0'
        elif filterSetNumber == 1:
            self.root.dm6000b.cubeTurret.cube = 'CYmC0'
        else:
            raise ValueError('filterSetNumber must be 0 or 1')
        time.sleep(1)
        for positionSet in ('control', 'exp'):
            positions = self.positions_control if positionSet == 'control' else self.positions_exp
            for positionIndex, position in enumerate(positions):
                print('posindex: {}, position: {}'.format(positionIndex, position))
                self.root.dm6000b.stageX.pos, self.root.dm6000b.stageY.pos, self.root.dm6000b.stageZ.pos = position
                self.root.dm6000b.waitForReady()
                self.root.brightfieldLed.enabled = True
                self.root.brightfieldLed.power = 200
                self.root.dm6000b.lamp.tlShutterOpened = True
                self.root.camera._camera.AT_Flush()
                buffers = [self.root.camera.makeAcquisitionBuffer() for i in range(imageCount)]
                self.root.camera.shutter = self.root.camera.Shutter.Rolling
                self.root.camera.triggerMode = self.root.camera.TriggerMode.Software
                self.root.camera.cycleMode = self.root.camera.CycleMode.Fixed
                # 20ms brightfield exposure time
                self.root.camera.exposureTime = 0.020
                self.root.camera.frameCount = imageCount
                for buffer in buffers:
                    self.root.camera._camera.AT_QueueBuffer(buffer)
                self.root.camera._camera.AT_Command(self.root.camera.Feature.AcquisitionStart)
                time.sleep(1)
                self.root.camera.commandSoftwareTrigger()
                time.sleep(0.040)
                self.root.brightfieldLed.enabled = False
                self.root.dm6000b.lamp.tlShutterOpened = False
                # 300ms fluorescence exposure time
                self.root.camera.exposureTime = 0.300
                if filterSetNumber == 0:
                    self.root.lumencor.UVEnabled = True
                    self.root.lumencor.UVPower = 255
                    time.sleep(1)
                    self.root.camera.commandSoftwareTrigger()
                    time.sleep(0.320)
                    self.root.lumencor.UVEnabled = False
                    self.root.lumencor.cyanEnabled = True
                    self.root.lumencor.cyanPower = 255
                    time.sleep(0.08)
                    self.root.camera.commandSoftwareTrigger()
                    time.sleep(0.320)
                    self.root.lumencor.cyanEnabled = False
                    self.root.lumencor.greenEnabled = True
                    self.root.lumencor.greenPower = 255
                    time.sleep(0.08)
                    self.root.camera.commandSoftwareTrigger()
                    time.sleep(0.320)
                    self.root.lumencor.disable()
                    names = ['bf-DFTr', 'DAPI', 'FITC', 'TRITC']
                elif filterSetNumber == 1:
                    self.root.lumencor.blueEnabled = True
                    self.root.lumencor.bluePower = 255
                    time.sleep(1)
                    self.root.camera.commandSoftwareTrigger()
                    time.sleep(0.320)
                    self.root.lumencor.blueEnabled = False
                    self.root.lumencor.tealEnabled = True
                    self.root.lumencor.tealPower = 255
                    time.sleep(0.08)
                    self.root.camera.commandSoftwareTrigger()
                    time.sleep(0.320)
                    self.root.lumencor.tealEnabled = False
                    self.root.lumencor.greenEnabled = True
                    self.root.lumencor.greenPower = 255
                    time.sleep(0.08)
                    self.root.camera.commandSoftwareTrigger()
                    time.sleep(0.320)
                    self.root.lumencor.disable()
                    names = ['bf-CYmC', 'CFP', 'YFP', 'mCherry']
                for i in range(imageCount):
                    self.root.camera._camera.AT_WaitBuffer(1000)
                self.root.camera._camera.AT_Command(self.root.camera.Feature.AcquisitionStop)
                for i in range(imageCount):
                    imFP = self.out_dir / '{}_{}_{:04}_{}.png'.format(self.prefix, positionSet, positionIndex, names[i])
                    if rw is not None:
                        rw.showImage(buffers[i])
                    skio.imsave(str(imFP), buffers[i])
