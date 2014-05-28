# Copyright 2014 WUSTL ZPLAB

import ctypes
import numpy
import threading
from PyQt5 import QtCore
from acquisition.andor.andor_exception import AndorException
from acquisition.andor._andor import _Camera
from acquisition.device import DeviceException, ThreadedDevice, ThreadedDeviceWorker

class Camera(ThreadedDevice):
    '''This class provides a Device wrapper around _Camera, which is a boost::python based C++ module that provides
    an interface to the C Andor SDK3 API which is direct save for using enums in place of strings for identifying
    commands and parameters.  References to these enums are provided by Camera for your convenience.  For example:

    from acquisition.andor.andor import Camera
    c = Camera(0)
    # Long way
    c.shutter = acquisition.andor._andor._Camera.Shutter.Global
    # Convienent way
    c.shutter = c.Global

    Note that for this device, the device thread is used only for AT_WaitBuffer() calls.'''

    @staticmethod
    def getDeviceNames():
        '''This function makes Andor API calls that tend to run slowly and so can take a second or two to complete.'''
        return list(_Camera.getDeviceNames())

    Feature = _Camera.Feature
    Shutter = _Camera.Shutter
    SimplePreAmp = _Camera.SimplePreAmp
    TemperatureStatus = _Camera.TemperatureStatus
    TriggerMode = _Camera.TriggerMode
    Binning = _Camera.Binning
    AuxiliaryOutSource = _Camera.AuxiliaryOutSource
    CycleMode = _Camera.CycleMode
    FanSpeed = _Camera.FanSpeed
    PixelEncoding = _Camera.PixelEncoding

    accumulateCountChanged = QtCore.pyqtSignal(int)
    aoiHeightChanged = QtCore.pyqtSignal(int)
    aoiLeftChanged = QtCore.pyqtSignal(int)
    aoiStrideChanged = QtCore.pyqtSignal(int)
    aoiTopChanged = QtCore.pyqtSignal(int)
    aoiWidthChanged = QtCore.pyqtSignal(int)
    bytesPerPixelChanged = QtCore.pyqtSignal(float) # \/
    exposureTimeChanged = QtCore.pyqtSignal(float)
    frameCountChanged = QtCore.pyqtSignal(int)
    frameRateChanged = QtCore.pyqtSignal(float)
    imageSizeBytesChanged = QtCore.pyqtSignal(int)
    readoutTimeChanged = QtCore.pyqtSignal(float)
    sensorCoolingChanged = QtCore.pyqtSignal(bool)
    spuriousNoiseFilterChanged = QtCore.pyqtSignal(bool)
    timestampClockFrequencyChanged = QtCore.pyqtSignal(int)
    simplePreAmpChanged = QtCore.pyqtSignal(_Camera.SimplePreAmp) # /\
    shutterChanged = QtCore.pyqtSignal(_Camera.Shutter)
    triggerModeChanged = QtCore.pyqtSignal(_Camera.TriggerMode)
    binningChanged = QtCore.pyqtSignal(_Camera.Binning)
    auxiliaryOutSourceChanged = QtCore.pyqtSignal(_Camera.AuxiliaryOutSource)
    cycleModeChanged = QtCore.pyqtSignal(_Camera.CycleMode)
    fanSpeedChanged = QtCore.pyqtSignal(_Camera.FanSpeed)
    pixelEncodingChanged = QtCore.pyqtSignal(_Camera.PixelEncoding)

    def __init__(self, parent=None, deviceName='Andor Zyla 5.5', andorDeviceIndex=0):
        super().__init__(_CameraWorker(self), parent, deviceName)
        self._camera = _Camera(andorDeviceIndex)
        self._propLock = threading.RLock()
        self._cmdLock = threading.RLock()
        self._callbackTokens = []
        with self._propLock, self._cmdLock:
            # Cached properties that do not change and therefore only need to be read once
            self._cameraModel = self._camera.AT_GetString(_Camera.Feature.CameraModel)
            self._interfaceType = self._camera.AT_GetString(_Camera.Feature.InterfaceType)
            self._sensorHeight = self._camera.AT_GetInt(_Camera.Feature.SensorHeight)
            self._sensorWidth = self._camera.AT_GetInt(_Camera.Feature.SensorWidth)
            self._serialNumber = self._camera.AT_GetString(_Camera.Feature.SerialNumber)
            # Cached properties that, when changed, cause callback execution updating the cache and emitting an xxxxChanged signal
            self._accumulateCount = self._camera.AT_GetInt(_Camera.Feature.AccumulateCount)
            self._callbackTokens.append(self._camera.AT_RegisterFeatureCallback(_Camera.Feature.AccumulateCount, self._accumulateCountCb))
            self._aoiHeight = self._camera.AT_GetInt(_Camera.Feature.AOIHeight)
            self._callbackTokens.append(self._camera.AT_RegisterFeatureCallback(_Camera.Feature.AOIHeight, self._aoiHeightCb))
            self._aoiLeft = self._camera.AT_GetInt(_Camera.Feature.AOILeft)
            self._callbackTokens.append(self._camera.AT_RegisterFeatureCallback(_Camera.Feature.AOILeft, self._aoiLeftCb))
            self._aoiStride = self._camera.AT_GetInt(_Camera.Feature.AOIStride)
            self._callbackTokens.append(self._camera.AT_RegisterFeatureCallback(_Camera.Feature.AOIStride, self._aoiStrideCb))
            self._aoiTop = self._camera.AT_GetInt(_Camera.Feature.AOITop)
            self._callbackTokens.append(self._camera.AT_RegisterFeatureCallback(_Camera.Feature.AOITop, self._aoiTopCb))
            self._aoiWidth = self._camera.AT_GetInt(_Camera.Feature.AOIWidth)
            self._callbackTokens.append(self._camera.AT_RegisterFeatureCallback(_Camera.Feature.AOIWidth, self._aoiWidthCb))
            self._bytesPerPixel = self._camera.AT_GetFloat(_Camera.Feature.BytesPerPixel)
            self._callbackTokens.append(self._camera.AT_RegisterFeatureCallback(_Camera.Feature.BytesPerPixel, self._bytesPerPixelCb))
            self._simplePreAmp = self._camera.simplePreAmp
            self._callbackTokens.append(self._camera.AT_RegisterFeatureCallback(_Camera.Feature.SimplePreAmpGainControl, self._simplePreAmpCb))
            self._shutter = self._camera.shutter
            self._callbackTokens.append(self._camera.AT_RegisterFeatureCallback(_Camera.Feature.ElectronicShutteringMode, self._shutterCb))
            self._triggerMode = self._camera.triggerMode
            self._callbackTokens.append(self._camera.AT_RegisterFeatureCallback(_Camera.Feature.TriggerMode, self._triggerModeCb))
            self._binning = self._camera.binning
            self._callbackTokens.append(self._camera.AT_RegisterFeatureCallback(_Camera.Feature.AOIBinning, self._binningCb))
            self._auxiliaryOutSource = self._camera.auxiliaryOutSource
            self._callbackTokens.append(self._camera.AT_RegisterFeatureCallback(_Camera.Feature.AuxiliaryOutSource, self._auxiliaryOutSourceCb))
            self._cycleMode = self._camera.cycleMode
            self._callbackTokens.append(self._camera.AT_RegisterFeatureCallback(_Camera.Feature.CycleMode, self._cycleModeCb))
            self._fanSpeed = self._camera.fanSpeed
            self._callbackTokens.append(self._camera.AT_RegisterFeatureCallback(_Camera.Feature.FanSpeed, self._fanSpeedCb))
            self._pixelEncoding = self._camera.pixelEncoding
            self._callbackTokens.append(self._camera.AT_RegisterFeatureCallback(_Camera.Feature.PixelEncoding, self._pixelEncodingCb))

    def _destroyedSlot(self):
        with self._cmdLock:
            for crt in self._callbackTokens:
                self._camera.AT_UnregisterFeatureCallback(crt)
            try:
                # Attempt to stop acquisition in case device thread is blocking on AT_WaitBuffer(..) that would never
                # otherwise complete
                self._camera.AT_Command(self.Feature.AcquisitionStop)
            except AndorException as e:
                pass
        super()._destroyedSlot()


    @QtCore.pyqtProperty(str)
    def cameraModel(self):
        return self._cameraModel

    
    @QtCore.pyqtProperty(str)
    def interfaceType(self):
        return self._interfaceType


    @QtCore.pyqtProperty(int)
    def sensorHeight(self):
        return self._sensorHeight


    @QtCore.pyqtProperty(int)
    def sensorWidth(self):
        return self._sensorWidth


    @QtCore.pyqtProperty(float)
    def sensorTemperature(self):
        '''Sensor temperature may change at any time, and the Andor SDK has no mechanism for notifying us when it has,
        so every get of this property causes the current value to be retrieved from the camera and returned.'''
        with self._cmdLock:
            return self._camera.AT_GetFloat(_Camera.Feature.SensorTemperature)


    @QtCore.pyqtProperty(int)
        '''As with sensorTemperature, this property's value is not cached and each read causes the current value to be
        retrieved from the camera.'''
        with self._cmdLock:
            return self._camera.AT_GetInt(_Camera.Feature.TimestampClock)


    @QtCore.pyqtProperty(int)
    def accumulateCount(self):
        with self._propLock:
            return self._accumulateCount

    @accumulateCount.setter
    def accumulateCount(self, accumulateCount):
        with self._cmdLock:
            self._camera.AT_SetInt(_Camera.Feature.AccumulateCount, accumulateCount)

    def _accumulateCountCb(self, feature):
        with self._propLock, self._cmdLock:
            self._accumulateCount = self._camera.AT_GetInt(_Camera.Feature.AccumulateCount)
            self.accumulateCountChanged.emit(self._accumulateCount)


    @QtCore.pyqtProperty(int)
    def aoiHeight(self):
        with self._propLock:
            return self._aoiHeight

    @aoiHeight.setter
    def aoiHeight(self, aoiHeight):
        with self._cmdLock:
            self._camera.AT_SetInt(_Camera.Feature.AOIHeight, aoiHeight)

    def _aoiHeightCb(self, feature):
        with self._propLock, self._cmdLock:
            self._aoiHeight = self._camera.AT_GetInt(_Camera.Feature.AOIHeight)
            self.aoiHeightChanged.emit(self._aoiHeight)


    @QtCore.pyqtProperty(int)
    def aoiLeft(self):
        with self._propLock:
            return self._aoiLeft

    @aoiLeft.setter
    def aoiLeft(self, aoiLeft):
        with self._cmdLock:
            self._camera.AT_SetInt(_Camera.Feature.AOILeft, aoiLeft)

    def _aoiLeftCb(self, feature):
        with self._propLock, self._cmdLock:
            self._aoiLeft = self._camera.AT_GetInt(_Camera.Feature.AOILeft)
            self.aoiLeftChanged.emit(self._aoiLeft)


    @QtCore.pyqtProperty(int)
    def aoiStride(self):
        with self._propLock:
            return self._aoiStride

    @aoiStride.setter
    def aoiStride(self, aoiStride):
        with self._cmdLock:
            self._camera.AT_SetInt(_Camera.Feature.AOIStride, aoiStride)

    def _aoiStrideCb(self, feature):
        with self._propLock, self._cmdLock:
            self._aoiStride = self._camera.AT_GetInt(_Camera.Feature.AOIStride)
            self.aoiStrideChanged.emit(self._aoiStride)


    @QtCore.pyqtProperty(int)
    def aoiTop(self):
        with self._propLock:
            return self._aoiTop

    @aoiTop.setter
    def aoiTop(self, aoiTop):
        with self._cmdLock:
            self._camera.AT_SetInt(_Camera.Feature.AOITop, aoiTop)

    def _aoiTopCb(self, feature):
        with self._propLock, self._cmdLock:
            self._aoiTop = self._camera.AT_GetInt(_Camera.Feature.AOITop)
            self.aoiTopChanged.emit(self._aoiTop)


    @QtCore.pyqtProperty(int)
    def aoiWidth(self):
        with self._propLock:
            return self._aoiWidth

    @aoiWidth.setter
    def aoiWidth(self, aoiWidth):
        with self._cmdLock:
            self._camera.AT_SetInt(_Camera.Feature.AOIWidth, aoiWidth)

    def _aoiWidthCb(self, feature):
        with self._propLock, self._cmdLock:
            self._aoiWidth = self._camera.AT_GetInt(_Camera.Feature.AOIWidth)
            self.aoiWidthChanged.emit(self._aoiWidth)


    @QtCore.pyqtProperty(float)
    def bytesPerPixel(self):
        with self._propLock:
            return self._bytesPerPixel

    def _bytesPerPixelCb(self, feature):
        with self._propLock, self._cmdLock:
            self._bytesPerPixel = self._camera.AT_GetFloat(_Camera.Feature.BytesPerPixel)
            self.bytesPerPixelChanged.emit(self._bytesPerPixel)


    @QtCore.pyqtProperty(_Camera.SimplePreAmp, notify=simplePreAmpChanged)
    def simplePreAmp(self):
        with self._propLock:
            return self._simplePreAmp

    @simplePreAmp.setter
    def simplePreAmp(self, simplePreAmp):
        with self._cmdLock:
            self._camera.simplePreAmp = simplePreAmp

    def _simplePreAmpCb(self, feature):
        with self._propLock, self._cmdLock:
            self._simplePreAmp = self._camera.simplePreAmp
            self.simplePreAmpChanged.emit(self._simplePreAmp)


    @QtCore.pyqtProperty(_Camera.Shutter, notify=shutterChanged)
    def shutter(self):
        with self._propLock:
            return self._shutter

    @shutter.setter
    def shutter(self, shutter):
        with self._cmdLock:
            self._camera.shutter = shutter

    def _shutterCb(self, feature):
        with self._propLock, self._cmdLock:
            self._shutter = self._camera.shutter
            self.shutterChanged.emit(self._shutter)


    @QtCore.pyqtProperty(_Camera.TriggerMode, notify=triggerModeChanged)
    def triggerMode(self):
        with self._propLock:
            return self._triggerMode

    @triggerMode.setter
    def triggerMode(self, triggerMode):
        with self._cmdLock:
            self._camera.triggerMode = triggerMode

    def _triggerModeCb(self, feature):
        with self._propLock, self._cmdLock:
            self._triggerMode = self._camera.triggerMode
            self.triggerModeChanged.emit(self._triggerMode)


    @QtCore.pyqtProperty(_Camera.Binning, notify=binningChanged)
    def binning(self):
        with self._propLock:
            return self._binning

    @binning.setter
    def binning(self, binning):
        with self._cmdLock:
            self._camera.binning = binning

    def _binningCb(self, feature):
        with self._propLock, self._cmdLock:
            self._binning = self._camera.binning
            self.binningChanged.emit(self._binning)


    @QtCore.pyqtProperty(_Camera.AuxiliaryOutSource, notify=auxiliaryOutSourceChanged)
    def auxiliaryOutSource(self):
        with self._propLock:
            return self._auxiliaryOutSource

    @auxiliaryOutSource.setter
    def auxiliaryOutSource(self, auxiliaryOutSource):
        with self._cmdLock:
            self._camera.auxiliaryOutSource = auxiliaryOutSource

    def _auxiliaryOutSourceCb(self, feature):
        with self._propLock, self._cmdLock:
            self._auxiliaryOutSource = self._camera.auxiliaryOutSource
            self.auxiliaryOutSourceChanged.emit(self._auxiliaryOutSource)


    @QtCore.pyqtProperty(_Camera.CycleMode, notify=cycleModeChanged)
    def cycleMode(self):
        with self._propLock:
            return self._cycleMode

    @cycleMode.setter
    def cycleMode(self, cycleMode):
        with self._cmdLock:
            self._camera.cycleMode = cycleMode

    def _cycleModeCb(self, feature):
        with self._propLock, self._cmdLock:
            self._cycleMode = self._camera.cycleMode
            self.cycleModeChanged.emit(self._cycleMode)


    @QtCore.pyqtProperty(_Camera.FanSpeed, notify=fanSpeedChanged)
    def fanSpeed(self):
        with self._propLock:
            return self._fanSpeed

    @fanSpeed.setter
    def fanSpeed(self, fanSpeed):
        with self._cmdLock:
            self._camera.fanSpeed = fanSpeed

    def _fanSpeedCb(self, feature):
        with self._propLock, self._cmdLock:
            self._fanSpeed = self._camera.fanSpeed
            self.fanSpeedChanged.emit(self._fanSpeed)


    @QtCore.pyqtProperty(_Camera.PixelEncoding, notify=pixelEncodingChanged)
    def pixelEncoding(self):
        '''Note that PixelEncoding is not set directly; it depends upon the current value of SimplePreAmp.'''
        with self._propLock:
            return self._pixelEncoding

    def _pixelEncodingCb(self, feature):
        with self._propLock, self._cmdLock:
            self._pixelEncoding = self._camera.pixelEncoding
            self.pixelEncodingChanged.emit(self._pixelEncoding)


#   def getPixelEncoding(self):
#       enumIndex = self._camera.AT_GetEnumIndex(self.Feature.PixelEncoding)
#       return self._camera.AT_GetEnumStringByIndex(self.Feature.PixelEncoding, enumIndex)
#
#   def getEnumStrings(self, feature):
#       return [self._camera.AT_GetEnumStringByIndex(feature, i) for i in range(self._camera.AT_GetEnumCount(feature))]
#
#   def getEnumString(self, feature):
#       return self._camera.AT_GetEnumStringByIndex(feature, self._camera.AT_GetEnumIndex(feature))
#
#   def setExposureTime(self, exposureTime):
#       '''Note that if exposureTime is less than the Camera's minimum exposure time as reported by the SDK,
#       then the minimum legal value is used.  Returns actual exposure time reported by SDK we set exposure time.'''
#       minExposureTime = self._camera.AT_GetFloatMin(self.Feature.ExposureTime)
#       if exposureTime < minExposureTime:
#           exposureTime = minExposureTime
#       self._camera.AT_SetFloat(self.Feature.ExposureTime, exposureTime)
#       return self._camera.AT_GetFloat(self.Feature.ExposureTime)

    def makeAcquisitionBuffer(self):
        aoiStride = self._camera.AT_GetInt(self.Feature.AOIStride)
        imageBufferSize = self._camera.AT_GetInt(self.Feature.ImageSizeBytes)
        if imageBufferSize <= 0:
            raise AndorException('ImageSizeBytes value retrieved from Andor API is <= 0.')
        if imageBufferSize % aoiStride != 0:
            raise AndorException('Value of ImageSizeBytes retrieved from Andor API is not divisible by AOIStride value.')
        return numpy.ndarray(shape=(imageBufferSize / aoiStride, aoiStride / 2), dtype=numpy.uint16, order='C')

    def acquireImage(self):
        imageBuffer = self.makeAcquisitionBuffer()

        # Queue acquisition buffer
        acquisitionTimeout = int(self._camera.AT_GetFloat(self.Feature.ExposureTime) * 3 * 1000)
        if acquisitionTimeout < 500:
            acquisitionTimeout = 500
        self._camera.AT_Flush()
        self._camera.AT_QueueBuffer(imageBuffer)

        # Initiate acquisition
        self._camera.AT_Command(self.Feature.AcquisitionStart)

        # Wait for acquisition to complete and verify that acquisition data was written to the acquisition buffer we queued
        acquiredBuffer = self._camera.AT_WaitBuffer(acquisitionTimeout)
        self._camera.AT_Command(self.Feature.AcquisitionStop)
        if acquiredBuffer != imageBuffer.ctypes.data_as(ctypes.c_void_p).value:
            raise AndorException('Acquired image buffer has different address than queued image buffer.')

        return imageBuffer[:self._camera.AT_GetInt(self.Feature.AOIHeight), :self._camera.AT_GetInt(self.Feature.AOIWidth)]

#   @property
#   def model(self):
#       return self._camera.AT_GetString(self.Feature.CameraModel)
#
#   @property
#   def acquiring(self):
#       return self._camera.AT_GetBool(self.Feature.CameraAcquiring)
#
#
#   @property
#   def exposureTime(self):
#       return self._camera.AT_GetFloat(self.Feature.ExposureTime)
#
#   @exposureTime.setter
#   def exposureTime(self, exposureTime):
#       self.setExposureTime(exposureTime)
#
#   @property
#   def minExposureTime(self):
#       return self._camera.AT_GetFloatMin(self.Feature.ExposureTime)
#
#   @property
#   def maxExposureTime(self):
#       return self._camera.AT_GetFloatMax(self.Feature.ExposureTime)
#
#
#   @property
#   def overlap(self):
#       return self._camera.AT_GetBool(self.Feature.Overlap)
#
#   @overlap.setter
#   def overlap(self, overlap):
#       self._camera.AT_SetBool(self.Feature.Overlap, overlap)
#
#
#   @property
#   def frameRate(self):
#       return self._camera.AT_GetFloat(self.Feature.FrameRate)
#
#   @frameRate.setter
#   def frameRate(self, frameRate):
#       self._camera.AT_SetFloat(self.Feature.FrameRate, frameRate)
#
#   @property
#   def minFrameRate(self):
#       return self._camera.AT_GetFloatMin(self.Feature.FrameRate)
#
#   @property
#   def maxFrameRate(self):
#       return self._camera.AT_GetFloatMax(self.Feature.FrameRate)

class _CameraWorker(ThreadedDeviceWorker):
    def __init__(self, device):
        super().__init__(device)

#   def initProps(self):
#       with self._device._cmdLock, self._device._propLock:
#           self._device._exposureTime = self._device._camera.AT_
#           self._device._minExposureTime = self._device._camera.AT_GetFloat(self._device.Feature.FrameRate)
