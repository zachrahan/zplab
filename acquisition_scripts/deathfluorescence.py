from PyQt5 import Qt
import pathlib
from skimage import io as skio
for function in ('imread', 'imsave', 'imread_collection'):
    skio.use_plugin('freeimage', function)
import time

class DeathFluorescence(Qt.QObject):
    def __init__(self, root, timeInterval, outPath, imagePrefix, rw=None, runCount=None):
        super().__init__()
        self.root = root
        self.timeInterval = timeInterval
        self.outPath = pathlib.Path(outPath)
        self.runCount = runCount
        self.currRun = 0
        if not self.outPath.exists():
            self.outPath.mkdir(parents=True)
        self.imagePrefix = imagePrefix
        self.rw = rw

    def startAutomatedAcquisition(self):
        self.runTimer = Qt.QTimer(self)
        self.runTimer.setSingleShot(False)
        self.runTimer.timeout.connect(self.executeRun)
        self.runTimer.start(self.timeInterval * 1000)
        self.executeRun()

    def executeRun(self):
        self.root.dm6000b.lamp.ilShutterOpened = True
        self.root.dm6000b.lamp.tlShutterOpened = True
        runStartTime = time.time()
        self.root.brightfieldLed.enabled = True
        self.root.brightfieldLed.power = 255
        self.root.camera._camera.AT_Flush()
        buffers = [self.root.camera.makeAcquisitionBuffer() for i in range(4)]
        self.root.camera.shutter = self.root.camera.Shutter.Rolling
        self.root.camera.triggerMode = self.root.camera.TriggerMode.Software
        self.root.camera.cycleMode = self.root.camera.CycleMode.Fixed
        self.root.camera.frameCount = 4
        for buffer in buffers:
            self.root.camera._camera.AT_QueueBuffer(buffer)
        self.root.camera._camera.AT_Command(self.root.camera.Feature.AcquisitionStart)
        time.sleep(0.08)
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
        for i in range(4):
            print(i)
            self.root.camera._camera.AT_WaitBuffer(1000)
        self.root.camera._camera.AT_Command(self.root.camera.Feature.AcquisitionStop)

        self.saveImage(buffers[0], 'bf', runStartTime)
        self.saveImage(buffers[1], 'uv', runStartTime)
        self.saveImage(buffers[2], 'cyan', runStartTime)
        self.saveImage(buffers[3], 'greenyellow', runStartTime)

        self.currRun += 1
        if self.runCount is not None and self.currRun >= self.runCount:
            self.runTimer.stop()

    def saveImage(self, image, type_, time_):
        imFP = self.outPath / '{}_{}_{}.png'.format(self.imagePrefix, type_, time_)
        if self.rw is not None:
            self.rw.showImage(image)
        skio.imsave(str(imFP), image)
