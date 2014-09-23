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
        self.stop_button = Qt.QPushButton('stop getting positions')
        self.stop_button.clicked.connect(self.stop_getting_positions)
        self.stop_button.show()
        self.root.pedals.pedalUpChanged.connect(self.on_pedal_up)

    def on_pedal_up(self, pedal, isUp):
        if not isUp:
            pos = (self.root.dm6000b.stageX.pos, self.root.dm6000b.stageY.pos, self.root.dm6000b.stageZ.pos)
            pl = self.positions_control if pedal == 0 else self.positions_exp
            pl.append(pos)

    def stop_getting_positions(self):
        self.root.pedals.pedalUpChanged.disconnect(self.on_pedal_up)
        self.stop_button.close()
        del self.stop_button

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
        ## NEED TO EXPLICITLY SET EXPOSURE TIMES -- 20 ms for brightfield and 150 ms for fluorescence
        for positionSet in ('control', 'exp'):
            positions = self.positions_control if positionSet is 'control' else self.positions_exp
            for positionIndex, position in enumerate(positions):
                self.root.dm6000b.stageX.pos, self.root.dm6000b.stageY.pos, self.root.dm6000b.stageZ.pos = position
                self.root.brightfieldLed.enabled = True
                self.root.brightfieldLed.power = 200
                self.root.camera._camera.AT_Flush()
                buffers = [self.root.camera.makeAcquisitionBuffer() for i in range(imageCount)]
                self.root.camera.shutter = self.root.camera.Shutter.Rolling
                self.root.camera.triggerMode = self.root.camera.TriggerMode.Software
                self.root.camera.cycleMode = self.root.camera.CycleMode.Fixed
                self.root.camera.frameCount = imageCount
                for buffer in buffers:
                    self.root.camera._camera.AT_QueueBuffer(buffer)
                self.root.camera._camera.AT_Command(self.root.camera.Feature.AcquisitionStart)
                time.sleep(0.08)
                if filterSetNumber == 0:
                    self.root.camera.commandSoftwareTrigger()
                    time.sleep(0.020)
                    self.root.brightfieldLed.enabled = False
                    self.root.lumencor.UVEnabled = True
                    self.root.lumencor.UVPower = 255
                    time.sleep(0.08)
                    self.root.camera.commandSoftwareTrigger()
                    time.sleep(0.020)
                    self.root.lumencor.UVEnabled = False
                    self.root.lumencor.cyanEnabled = True
                    self.root.lumencor.cyanPower = 255
                    time.sleep(0.08)
                    self.root.camera.commandSoftwareTrigger()
                    time.sleep(0.020)
                    self.root.lumencor.cyanEnabled = False
                    self.root.lumencor.greenEnabled = True
                    self.root.lumencor.greenPower = 255
                    time.sleep(0.08)
                    self.root.camera.commandSoftwareTrigger()
                    time.sleep(0.020)
                    self.root.lumencor.disable()
                    names = ['bf-DFTr', 'DAPI', 'FITC', 'TRITC']
                elif filterSetNumber == 1:
                    self.root.camera.commandSoftwareTrigger()
                    time.sleep(0.020)
                    self.root.brightfieldLed.enabled = False
                    self.root.lumencor.blueEnabled = True
                    self.root.lumencor.bluePower = 255
                    time.sleep(0.08)
                    self.root.camera.commandSoftwareTrigger()
                    time.sleep(0.020)
                    self.root.lumencor.blueEnabled = False
                    self.root.lumencor.tealEnabled = True
                    self.root.lumencor.tealPower = 255
                    time.sleep(0.08)
                    self.root.camera.commandSoftwareTrigger()
                    time.sleep(0.020)
                    self.root.lumencor.tealEnabled = False
                    self.root.lumencor.greenEnabled = True
                    self.root.lumencor.greenPower = 255
                    time.sleep(0.08)
                    self.root.camera.commandSoftwareTrigger()
                    time.sleep(0.020)
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

#   def executeRun(self):
#       self.root.dm6000b.lamp.ilShutterOpened = True
#       self.root.dm6000b.lamp.tlShutterOpened = True
#       runStartTime = time.time()
#       self.root.brightfieldLed.enabled = True
#       self.root.brightfieldLed.power = 255
#       self.root.camera._camera.AT_Flush()
#       buffers = [self.root.camera.makeAcquisitionBuffer() for i in range(4)]
#       self.root.camera.shutter = self.root.camera.Shutter.Rolling
#       self.root.camera.triggerMode = self.root.camera.TriggerMode.Software
#       self.root.camera.cycleMode = self.root.camera.CycleMode.Fixed
#       self.root.camera.frameCount = 4
#       for buffer in buffers:
#           self.root.camera._camera.AT_QueueBuffer(buffer)
#       self.root.camera._camera.AT_Command(self.root.camera.Feature.AcquisitionStart)
#       time.sleep(0.08)
#       self.root.camera.commandSoftwareTrigger()
#       time.sleep(0.020)
#       self.root.brightfieldLed.enabled = False
#       self.root.lumencor.UVEnabled = True
#       self.root.lumencor.UVPower = 255
#       time.sleep(0.08)
#       self.root.camera.commandSoftwareTrigger()
#       time.sleep(0.020)
#       self.root.lumencor.UVEnabled = False
#       self.root.lumencor.cyanEnabled = True
#       self.root.lumencor.cyanPower = 255
#       time.sleep(0.08)
#       self.root.camera.commandSoftwareTrigger()
#       time.sleep(0.020)
#       self.root.lumencor.cyanEnabled = False
#       self.root.lumencor.greenEnabled = True
#       self.root.lumencor.greenPower = 255
#       time.sleep(0.08)
#       self.root.camera.commandSoftwareTrigger()
#       time.sleep(0.020)
#       self.root.lumencor.disable()
#       for i in range(4):
#           print(i)
#           self.root.camera._camera.AT_WaitBuffer(1000)
#       self.root.camera._camera.AT_Command(self.root.camera.Feature.AcquisitionStop)
#
#       self.saveImage(buffers[0], 'bf', runStartTime)
#       self.saveImage(buffers[1], 'uv', runStartTime)
#       self.saveImage(buffers[2], 'cyan', runStartTime)
#       self.saveImage(buffers[3], 'greenyellow', runStartTime)
#
#       self.currRun += 1
#       if self.runCount is not None and self.currRun >= self.runCount:
#           self.runTimer.stop()
#
#   def saveImage(self, image, type_, time_):
#       imFP = self.outPath / '{}_{}_{}.png'.format(self.imagePrefix, type_, time_)
#       if self.rw is not None:
#           self.rw.showImage(image)
#       skio.imsave(str(imFP), image)
