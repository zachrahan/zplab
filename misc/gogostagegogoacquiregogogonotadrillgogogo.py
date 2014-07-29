from acquisition.peltier.incubator import Incubator
from acquisition.pedals.pedal import WaitPedal

wp = WaitPedal('/dev/ttyACM1')

def getstage():
    return root.dm6000b.stageX.pos, root.dm6000b.stageY.pos, root.dm6000b.stageZ.pos

def memorize():
    poss = []
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



high_p = [(8006204, 1544254, 6713725),
 (7957108, 1476661, 6711389),
 (7885514, 1485325, 6710843),
 (7864087, 1514584, 6712133),
 (7820608, 1468359, 6710748),
 (7714176, 1460169, 6714056),
 (7627575, 1379070, 6718864),
 (7892271, 1265055, 6711679),
 (8060227, 1242943, 6712677),
 (7782661, 1186181, 6713273),
 (7851175, 1179866, 6712913),
 (7901288, 1105463, 6713271),
 (7932698, 1070832, 6714884),
 (7845193, 1017317, 6716158)]

low_p = [(6415958, 1608594, 6712725),
 (6535418, 1546539, 6708559),
 (6515609, 1468518, 6708302),
 (6384263, 1475003, 6707718),
 (6239316, 1498154, 6710689),
 (6189054, 1469986, 6710439),
 (6331145, 1426239, 6707614),
 (6255883, 1387339, 6708714),
 (6457262, 1231102, 6708713),
 (6273437, 1180188, 6713117),
 (6638907, 1199397, 6711852),
 (6665253, 1270035, 6713300),
 (6773603, 1348285, 6714493)]


def saveImages(images, imageFilenamePrefix):
    for imageIndex, (bf, fl) in enumerate(images):
        skimage.io.imsave('{}_{:03}_bf.png'.format(imageFilenamePrefix, imageIndex), bf)
        skimage.io.imsave('{}_{:03}_fl.png'.format(imageFilenamePrefix, imageIndex), fl)

import time 
def gostage(xyz):
    x, y, z = xyz
    root.dm6000b.stageX.pos = x
    root.dm6000b.stageY.pos = y
    root.dm6000b.stageZ.pos = z
    root.dm6000b.waitForReady()

def acquire(position, sleep=0.1):
    print(position)
    gostage(position)
    root.camera.exposureTime = 0.01
    root.brightfieldLed.enabled, root.lumencor.greenEnabled = True, False
    root.dm6000b.lamp.tlShutterOpened = True
    time.sleep(sleep)
    bf = root.camera.acquireImage()
    root.brightfieldLed.enabled, root.lumencor.greenEnabled = False, True
    root.dm6000b.lamp.tlShutterOpened = False
    time.sleep(sleep)
    root.camera.exposureTime = 0.08
    fl = root.camera.acquireImage()
    root.brightfieldLed.enabled, root.lumencor.greenEnabled = False, False
    return bf, fl


from pathlib import Path
import time
from acquisition.peltier.incubator import Incubator

incubator = Incubator('/dev/ttyPeltier')

gps = [(6789349, 379502, 6705540),
       (6678956, 366751, 6726288),
       (6798787, 569569, 6743954),
       (6657517, 562448, 6743206),
       (6403389, 627105, 6751369),
       (6418864, 829184, 6751369),
       (6253339, 500030, 6735854),
       (6197321, 602129, 6714338),
       (6183833, 754658, 6735486),
       (6254329, 905754, 6754986),
       (6242137, 1567581, 6771920),
       (6389728, 1414501, 6774700),
       (6422259, 1583815, 6770482),
       (6621614, 1602771, 6766942),
       (6802849, 1615944, 6775462),
       (6782275, 2582297, 6704649),
       (6633425, 2603986, 6704649),
       (6439326, 2603986, 6704649),
       (6276077, 2609770, 6694967),
       (6083446, 2633737, 6708327)]

directory = Path('/mnt/scopearray/weekend')
acquiringWells = False
runIndex = 0
ledpower5x = 28
ledpower10x = 31
maxZ = 6760500
fineHalfSpan5x = 54667 / 2
fineHalfCount5x = 5
coarseHalfSpan5x = (488918 - 54667) / 2
coarseHalfCount5x = 3
fineHalfSpan10x = 18593 / 2
fineHalfCount10x = 5
coarseHalfSpan10x = (142583 - 18593) / 2
coarseHalfCount10x = 3

def gostageasync(x, y, z):
    root.dm6000b.stageX.pos = x
    root.dm6000b.stageY.pos = y
    root.dm6000b.stageZ.pos = z

def acquireAllWells():
    global acquiringWells
    global runIndex

    if acquiringWells:
        print('run #{}: Previous run still in progress and probably defunct... skipping this run.'.format(runIndex))
    else:
        print('run #{}: starting... '.format(runIndex))
        acquiringWells = True
        executeRun()
        print('run #{}: completed. '.format(runIndex))
        acquiringWells = False
        runIndex += 1

def executeRun():
    allFives = []
    allTens  = []
    root.brightfieldLed.enabled = True
    for i, xyz in enumerate(gps):
        x, y, z = xyz
        fives = []
        tens =  []
        doWell(i, x, y, z, fives, tens)
        allFives.append(fives)
        allTens.append(tens)
    root.brightfieldLed.enabled = False
    for i, fives in enumerate(allFives):
        outdir = outdirs[i] / '5x' / str(runIndex)
        if not outdir.exists():
            outdir.mkdir(parents=True)
        for image, z, temp in fives:
            filename = str(z)
            if z == gps[i][2]:
                filename += '_manual_z'
            filename += '_'
            filename += str(temp)
            filename += '.png'
            outpath = outdir / filename
            skimage.io.imsave(str(outpath), image)
    for i, tens in enumerate(allTens):
        outdir = outdirs[i] / '10x' / str(runIndex)
        if not outdir.exists():
            outdir.mkdir(parents=True)
        for image, z, temp in tens:
            filename = str(z)
            if z == gps[i][2]:
                filename += '_manual_z'
            filename += '_'
            filename += str(temp)
            filename += '.png'
            outpath = outdir / filename
            skimage.io.imsave(str(outpath), image)

def doWell(i, x, y, z, fives, tens):
    root.brightfieldLed.power = ledpower5x
    root.dm6000b.objectiveTurret.position = 1
    root.dm6000b.waitForReady()
    gostageasync(x, y, z)
    root.dm6000b.waitForReady()
    #### 5x ####
    # coarse interval images +Z
    z_s = list(numpy.linspace(z + coarseHalfSpan5x + fineHalfSpan5x, z + fineHalfSpan5x, num=coarseHalfCount5x, endpoint=False).astype(numpy.uint64))
    # fine interval images +Z
    z_s.extend(list(numpy.linspace(z + fineHalfSpan5x, z, num=fineHalfCount5x,  endpoint=False).astype(numpy.uint64)))
    # manually found Z
    z_s.append(z)
    # fine interval images -Z
    z_s.extend(list(reversed(numpy.linspace(z - fineHalfSpan5x,  z, num=fineHalfCount5x, endpoint=False).astype(numpy.uint64))))
    # coarse interval images -Z
    z_s.extend(list(reversed(numpy.linspace(z - coarseHalfSpan5x - fineHalfSpan5x, z - fineHalfSpan5x, num=coarseHalfCount5x, endpoint=False).astype(numpy.uint64))))
    for z_ in z_s:
        if z_ <= maxZ and z_ >= 0:
            print('5x: {}'.format(z_))
            root.dm6000b.stageZ.pos = z_
            root.dm6000b.stageZ.waitForReady()
            temp = incubator.get_current_temp()
            image = root.camera.acquireImage()
            rw.showImage(image)
            fives.append((image, z_, temp))
    #### 10x ####
    root.brightfieldLed.power = ledpower10x
    root.dm6000b.objectiveTurret.position = 2
    root.dm6000b.waitForReady()
    # coarse interval images +Z
    z_s = list(numpy.linspace(z + coarseHalfSpan10x + fineHalfSpan10x, z + fineHalfSpan10x, num=coarseHalfCount10x, endpoint=False).astype(numpy.uint64))
    # fine interval images +Z
    z_s.extend(list(numpy.linspace(z + fineHalfSpan10x, z, num=fineHalfCount10x,  endpoint=False).astype(numpy.uint64)))
    # manually found Z
    z_s.append(z)
    # fine interval images -Z
    z_s.extend(list(reversed(numpy.linspace(z - fineHalfSpan10x,  z, num=fineHalfCount10x, endpoint=False).astype(numpy.uint64))))
    # coarse interval images -Z
    z_s.extend(list(reversed(numpy.linspace(z - coarseHalfSpan10x - fineHalfSpan10x, z - fineHalfSpan10x, num=coarseHalfCount10x, endpoint=False).astype(numpy.uint64))))
    for z_ in z_s:
        if z_ <= maxZ and z_ >= 0:
            print('10x: {}'.format(z_))
            root.dm6000b.stageZ.pos = z_
            root.dm6000b.stageZ.waitForReady()
            temp = incubator.get_current_temp()
            image = root.camera.acquireImage()
            rw.showImage(image)
            tens.append((image, z_, temp))



# Make output directories
outdirs = []
for i, xyz in enumerate(gps):
    x, y, z = xyz
    outdir = directory / '{:02}_{:07}_{:07}_{:07}'.format(i, x, y, z)
    if not outdir.exists():
        outdir.mkdir()
    outdirs.append(outdir)

acqRunTimer = Qt.QTimer()
acqRunTimer.setSingleShot(False)
acqRunTimer.timeout.connect(acquireAllWells)
acqRunTimer.start(4 * 60 * 60 * 1000)

# Kick off first run (subsequent runs will be executed by acqRunTimer)
acquireAllWells()

def enough__stop_it_now():
    global acqRunTimer
    acqRunTimer.timeout.disconnect()
    acqRunTimer.stop()
