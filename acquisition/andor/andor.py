# Copyright 2014 WUSTL ZPLAB

import ctypes
import enum
import numpy
import threading
from PyQt5 import QtCore
from acquisition.andor.andor_exception import AndorException
from acquisition.andor._andor import _Camera
from acquisition.device import Device, DeviceException, ThreadedDevice, ThreadedDeviceWorker

class Camera(Device):
    '''This class provides a Device wrapper around _Camera, which is a boost::python based C++ module that provides
    an interface to the C Andor SDK3 API which is direct save for using enums in place of strings for identifying
    commands and parameters.  References to these enums are provided by Camera for your convenience.  For example:

    from acquisition.andor.andor import Camera
    c = Camera(0)
    # Long way
    c.shutter = acquisition.andor._andor._Camera.Shutter.Global
    # Convienent way
    c.shutter = c.Global

    There is generally a 1:1 mapping between properties presented by this class and Andor feature names described
    in the Andor SDK reference.

    Note that for this device, the device thread is used only for AT_WaitBuffer() calls.'''

    @staticmethod
    def getDeviceNames():
        '''This function makes Andor API calls that tend to run slowly and so can take a second or two to complete.'''
        return list(_Camera.getDeviceNames())

    @enum.unique
    class WaitBufferTimeout(enum.IntEnum):
        Default = 0
        Infinite = 1
        Override = 2

    # Much of the following code could be auto-generated at run time and, in fact, initially was.  However, it was tricky understand
    # and trickier still to debug.

    # Enums referenced for convenience
    AuxiliaryOutSource = _Camera.AuxiliaryOutSource
    Binning = _Camera.Binning
    CycleMode = _Camera.CycleMode
    FanSpeed = _Camera.FanSpeed
    Feature = _Camera.Feature
    IOSelector = _Camera.IOSelector
    PixelEncoding = _Camera.PixelEncoding
    PixelReadoutRate = _Camera.PixelReadoutRate
    Shutter = _Camera.Shutter
    SimplePreAmp = _Camera.SimplePreAmp
    TemperatureStatus = _Camera.TemperatureStatus
    TriggerMode = _Camera.TriggerMode

    # This signal is emitted when an image has been retrieved from the Andor API.  Its argument is a 2D numpy array
    # referring to the original image buffer.  Immediately after this signal is emitted, any references to the
    # numpy array retained by signal recipients will be the only extant references to the numpy array.  So, if nobody
    # is connected to this signal, the numpy array's reference count reaches zero and it along with its backing buffer
    # are dropped.  Making a new buffer 
    imageAcquired = QtCore.pyqtSignal(numpy.ndarray)

    # Signals for indicating to user that a Camera property has changed
    accumulateCountChanged = QtCore.pyqtSignal(int)
    acquisitionSequenceInProgressChanged = QtCore.pyqtSignal(bool)
    aoiHeightChanged = QtCore.pyqtSignal(int)
    aoiLeftChanged = QtCore.pyqtSignal(int)
    aoiStrideChanged = QtCore.pyqtSignal(int)
    aoiTopChanged = QtCore.pyqtSignal(int)
    aoiWidthChanged = QtCore.pyqtSignal(int)
    auxiliaryOutSourceChanged = QtCore.pyqtSignal(_Camera.AuxiliaryOutSource)
    binningChanged = QtCore.pyqtSignal(_Camera.Binning)
    bytesPerPixelChanged = QtCore.pyqtSignal(float)
    cycleModeChanged = QtCore.pyqtSignal(_Camera.CycleMode)
    exposureTimeChanged = QtCore.pyqtSignal(float)
    fanSpeedChanged = QtCore.pyqtSignal(_Camera.FanSpeed)
    frameCountChanged = QtCore.pyqtSignal(int)
    frameRateChanged = QtCore.pyqtSignal(float)
    imageSizeBytesChanged = QtCore.pyqtSignal(int)
    ioInvertChanged = QtCore.pyqtSignal(bool)
    ioSelectorChanged = QtCore.pyqtSignal(_Camera.IOSelector)
    maxInterfaceTransferRateChanged = QtCore.pyqtSignal(float)
    metadataEnabledChanged = QtCore.pyqtSignal(bool)
    metadataTimestampEnabledChanged = QtCore.pyqtSignal(bool)
    overlapChanged = QtCore.pyqtSignal(bool)
    pixelEncodingChanged = QtCore.pyqtSignal(_Camera.PixelEncoding)
    pixelReadoutRateChanged = QtCore.pyqtSignal(_Camera.PixelReadoutRate)
    readoutTimeChanged = QtCore.pyqtSignal(float)
    sensorCoolingChanged = QtCore.pyqtSignal(bool)
    shutterChanged = QtCore.pyqtSignal(_Camera.Shutter)
    simplePreAmpChanged = QtCore.pyqtSignal(_Camera.SimplePreAmp)
    spuriousNoiseFilterChanged = QtCore.pyqtSignal(bool)
    timestampClockFrequencyChanged = QtCore.pyqtSignal(int)
    triggerModeChanged = QtCore.pyqtSignal(_Camera.TriggerMode)
    # Note that the waitbufferTimeout property controls the behavior of this class and does not map to an Andor
    # API camera property
    waitBufferTimeoutChanged = QtCore.pyqtSignal(tuple)

    # Private signal used internally to queue next waitbuffer operation while allowing an opportunity for a stop signal
    # previously queued to preempt it
    _waitBuffer = QtCore.pyqtSignal()

    def __init__(self, parent=None, deviceName='Andor Zyla 5.5', andorDeviceIndex=0):
        '''Note: The deviceName argument sets the .deviceName property; it does not act as a criterion for choosing which Andor camera 
        to open.  That is controlled by the andorDeviceIndex argument exclusively.'''
        super().__init__(parent, deviceName)
        self._camera = _Camera(andorDeviceIndex)
        self._callbackTokens = []
        # Cached properties that do not change and therefore only need to be read once
        self._cameraModel = self._camera.AT_GetString(_Camera.Feature.CameraModel)
        self._interfaceType = self._camera.AT_GetString(_Camera.Feature.InterfaceType)
        self._pixelHeight = self._camera.AT_GetFloat(_Camera.Feature.PixelHeight)
        self._pixelWidth = self._camera.AT_GetFloat(_Camera.Feature.PixelWidth)
        self._sensorHeight = self._camera.AT_GetInt(_Camera.Feature.SensorHeight)
        self._sensorWidth = self._camera.AT_GetInt(_Camera.Feature.SensorWidth)
        self._serialNumber = self._camera.AT_GetString(_Camera.Feature.SerialNumber)
        # Cached properties that, when changed, cause callback execution updating the cache and emitting an xxxxChanged signal
        self._accumulateCount = self._camera.AT_GetInt(_Camera.Feature.AccumulateCount)
        self._callbackTokens.append(self._camera.AT_RegisterFeatureCallback(_Camera.Feature.AccumulateCount, self._accumulateCountCb))
        self._acquisitionSequenceInProgress = self._camera.AT_GetBool(_Camera.Feature.CameraAcquiring)
        self._callbackTokens.append(self._camera.AT_RegisterFeatureCallback(_Camera.Feature.CameraAcquiring, self._acquisitionSequenceInProgressCb))
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
        self._auxiliaryOutSource = self._camera.auxiliaryOutSource
        self._callbackTokens.append(self._camera.AT_RegisterFeatureCallback(_Camera.Feature.AuxiliaryOutSource, self._auxiliaryOutSourceCb))
        self._binning = self._camera.binning
        self._callbackTokens.append(self._camera.AT_RegisterFeatureCallback(_Camera.Feature.AOIBinning, self._binningCb))
        self._bytesPerPixel = self._camera.AT_GetFloat(_Camera.Feature.BytesPerPixel)
        self._callbackTokens.append(self._camera.AT_RegisterFeatureCallback(_Camera.Feature.BytesPerPixel, self._bytesPerPixelCb))
        self._cycleMode = self._camera.cycleMode
        self._callbackTokens.append(self._camera.AT_RegisterFeatureCallback(_Camera.Feature.CycleMode, self._cycleModeCb))
        self._exposureTime = self._camera.AT_GetFloat(_Camera.Feature.ExposureTime)
        self._callbackTokens.append(self._camera.AT_RegisterFeatureCallback(_Camera.Feature.ExposureTime, self._exposureTimeCb))
        self._fanSpeed = self._camera.fanSpeed
        self._callbackTokens.append(self._camera.AT_RegisterFeatureCallback(_Camera.Feature.FanSpeed, self._fanSpeedCb))
        self._frameCount = self._camera.AT_GetInt(_Camera.Feature.FrameCount)
        self._callbackTokens.append(self._camera.AT_RegisterFeatureCallback(_Camera.Feature.FrameCount, self._frameCountCb))
        self._frameRate = self._camera.AT_GetFloat(_Camera.Feature.FrameRate)
        self._callbackTokens.append(self._camera.AT_RegisterFeatureCallback(_Camera.Feature.FrameRate, self._frameRateCb))
        self._imageSizeBytes = self._camera.AT_GetInt(_Camera.Feature.ImageSizeBytes)
        self._callbackTokens.append(self._camera.AT_RegisterFeatureCallback(_Camera.Feature.ImageSizeBytes, self._imageSizeBytesCb))
        self._ioInvert = self._camera.AT_GetBool(_Camera.Feature.IOInvert);
        self._callbackTokens.append(self._camera.AT_RegisterFeatureCallback(_Camera.Feature.IOInvert, self._ioInvertCb))
        self._ioSelector = self._camera.ioSelector
        self._callbackTokens.append(self._camera.AT_RegisterFeatureCallback(_Camera.Feature.IOSelector, self._ioSelectorCb))
        self._maxInterfaceTransferRate = self._camera.AT_GetFloat(_Camera.Feature.MaxInterfaceTransferRate)
        self._callbackTokens.append(self._camera.AT_RegisterFeatureCallback(_Camera.Feature.MaxInterfaceTransferRate, self._maxInterfaceTransferRateCb))
        self._metadataEnabled = self._camera.AT_GetBool(_Camera.Feature.MetadataEnable)
        self._callbackTokens.append(self._camera.AT_RegisterFeatureCallback(_Camera.Feature.MetadataEnable, self._metadataEnabledCb))
        self._metadataTimestampEnabled = self._camera.AT_GetBool(_Camera.Feature.MetadataTimestamp)
        self._callbackTokens.append(self._camera.AT_RegisterFeatureCallback(_Camera.Feature.MetadataTimestamp, self._metadataTimestampEnabledCb))
        self._overlap = self._camera.AT_GetBool(_Camera.Feature.Overlap)
        self._callbackTokens.append(self._camera.AT_RegisterFeatureCallback(_Camera.Feature.Overlap, self._overlapCb))
        self._pixelEncoding = self._camera.pixelEncoding
        self._callbackTokens.append(self._camera.AT_RegisterFeatureCallback(_Camera.Feature.PixelEncoding, self._pixelEncodingCb))
        self._pixelReadoutRate = self._camera.pixelReadoutRate
        self._callbackTokens.append(self._camera.AT_RegisterFeatureCallback(_Camera.Feature.PixelReadoutRate, self._pixelReadoutRateCb))
        self._readoutTime = self._camera.AT_GetFloat(_Camera.Feature.ReadoutTime)
        self._callbackTokens.append(self._camera.AT_RegisterFeatureCallback(_Camera.Feature.ReadoutTime, self._readoutTimeCb))
        self._sensorCooling = self._camera.AT_GetBool(_Camera.Feature.SensorCooling)
        self._callbackTokens.append(self._camera.AT_RegisterFeatureCallback(_Camera.Feature.SensorCooling, self._sensorCoolingCb))
        self._shutter = self._camera.shutter
        self._callbackTokens.append(self._camera.AT_RegisterFeatureCallback(_Camera.Feature.ElectronicShutteringMode, self._shutterCb))
        self._simplePreAmp = self._camera.simplePreAmp
        self._callbackTokens.append(self._camera.AT_RegisterFeatureCallback(_Camera.Feature.SimplePreAmpGainControl, self._simplePreAmpCb))
        self._spuriousNoiseFilter = self._camera.AT_GetBool(_Camera.Feature.SpuriousNoiseFilter)
        self._callbackTokens.append(self._camera.AT_RegisterFeatureCallback(_Camera.Feature.SpuriousNoiseFilter, self._spuriousNoiseFilterCb))
        self._timestampClockFrequency = self._camera.AT_GetInt(_Camera.Feature.TimestampClockFrequency)
        self._callbackTokens.append(self._camera.AT_RegisterFeatureCallback(_Camera.Feature.TimestampClockFrequency, self._timestampClockFrequencyCb))
        self._triggerMode = self._camera.triggerMode
        self._callbackTokens.append(self._camera.AT_RegisterFeatureCallback(_Camera.Feature.TriggerMode, self._triggerModeCb))
        # Iff true, an acquisition sequence is in progress that was initiated through this class instance's interface
        self._acquisitionInitiatedByThisInstance = False
        # Having this be a queued connection allows a stop request to slip in between consecutive waitbuffers during
        # sequential acquisition
        self._waitBuffer.connect(self._waitBufferSlot, QtCore.Qt.QueuedConnection)
        self._waitBufferTimeout = (Camera.WaitBufferTimeout.Default,)

    def __del__(self):
        for crt in self._callbackTokens:
            self._camera.AT_UnregisterFeatureCallback(crt)
        self._callbackTokens = []
        try:
            # Attempt to stop acquisition in case device thread is blocking on AT_WaitBuffer(..) that would never
            # otherwise complete
            self._camera.AT_Command(self.Feature.AcquisitionStop)
        except AndorException as e:
            pass
        Device.__del__(self)

    def commandSoftwareTrigger(self):
        self._camera.AT_Command(_Camera.Feature.SoftwareTrigger)

    def commandTimestampClockReset(self):
        self._camera.AT_Command(_Camera.Feature.TimestampClockReset)


    @QtCore.pyqtProperty(str)
    def cameraModel(self):
        return self._cameraModel

    
    @QtCore.pyqtProperty(str)
    def interfaceType(self):
        return self._interfaceType


    @QtCore.pyqtProperty(float)
    def pixelHeight(self):
        return self._pixelHeight


    @QtCore.pyqtProperty(float)
    def pixelWidth(self):
        return self._pixelWidth


    @QtCore.pyqtProperty(int)
    def sensorHeight(self):
        return self._sensorHeight


    @QtCore.pyqtProperty(int)
    def sensorWidth(self):
        return self._sensorWidth


    @QtCore.pyqtProperty(str)
    def serialNumber(self):
        return self._serialNumber


    @QtCore.pyqtProperty(float)
    def sensorTemperature(self):
        '''Sensor temperature may change at any time, and the Andor SDK has no mechanism for notifying us when it has,
        so every get of this property causes the current value to be retrieved from the camera and returned.'''
        return self._camera.AT_GetFloat(_Camera.Feature.SensorTemperature)


    @QtCore.pyqtProperty(int)
    def timestampClock(self):
        '''As with sensorTemperature, this property's value is not cached and each read causes the current value to be
        retrieved from the camera.'''
        return self._camera.AT_GetInt(_Camera.Feature.TimestampClock)


    @QtCore.pyqtProperty(int, notify=accumulateCountChanged)
    def accumulateCount(self):
        return self._accumulateCount

    @accumulateCount.setter
    def accumulateCount(self, accumulateCount):
        self._camera.AT_SetInt(_Camera.Feature.AccumulateCount, accumulateCount)

    def _accumulateCountCb(self, feature):
        self._accumulateCount = self._camera.AT_GetInt(_Camera.Feature.AccumulateCount)
        self.accumulateCountChanged.emit(self._accumulateCount)
        return True


    @QtCore.pyqtProperty(bool, notify=acquisitionSequenceInProgressChanged)
    def acquisitionSequenceInProgress(self):
        return self._acquisitionSequenceInProgress

    def _acquisitionSequenceInProgressCb(self, feature):
        self._acquisitionSequenceInProgress = self._camera.AT_GetBool(_Camera.Feature.CameraAcquiring)


    @QtCore.pyqtProperty(int, notify=aoiHeightChanged)
    def aoiHeight(self):
        return self._aoiHeight

    @aoiHeight.setter
    def aoiHeight(self, aoiHeight):
        self._camera.AT_SetInt(_Camera.Feature.AOIHeight, aoiHeight)

    def _aoiHeightCb(self, feature):
        self._aoiHeight = self._camera.AT_GetInt(_Camera.Feature.AOIHeight)
        self.aoiHeightChanged.emit(self._aoiHeight)
        return True


    @QtCore.pyqtProperty(int, notify=aoiLeftChanged)
    def aoiLeft(self):
        return self._aoiLeft

    @aoiLeft.setter
    def aoiLeft(self, aoiLeft):
        self._camera.AT_SetInt(_Camera.Feature.AOILeft, aoiLeft)

    def _aoiLeftCb(self, feature):
        self._aoiLeft = self._camera.AT_GetInt(_Camera.Feature.AOILeft)
        self.aoiLeftChanged.emit(self._aoiLeft)
        return True


    @QtCore.pyqtProperty(int, notify=aoiStrideChanged)
    def aoiStride(self):
        return self._aoiStride

    @aoiStride.setter
    def aoiStride(self, aoiStride):
        self._camera.AT_SetInt(_Camera.Feature.AOIStride, aoiStride)

    def _aoiStrideCb(self, feature):
        self._aoiStride = self._camera.AT_GetInt(_Camera.Feature.AOIStride)
        self.aoiStrideChanged.emit(self._aoiStride)
        return True


    @QtCore.pyqtProperty(int, notify=aoiTopChanged)
    def aoiTop(self):
        return self._aoiTop

    @aoiTop.setter
    def aoiTop(self, aoiTop):
        self._camera.AT_SetInt(_Camera.Feature.AOITop, aoiTop)

    def _aoiTopCb(self, feature):
        self._aoiTop = self._camera.AT_GetInt(_Camera.Feature.AOITop)
        self.aoiTopChanged.emit(self._aoiTop)
        return True


    @QtCore.pyqtProperty(int, notify=aoiWidthChanged)
    def aoiWidth(self):
        return self._aoiWidth

    @aoiWidth.setter
    def aoiWidth(self, aoiWidth):
        self._camera.AT_SetInt(_Camera.Feature.AOIWidth, aoiWidth)

    def _aoiWidthCb(self, feature):
        self._aoiWidth = self._camera.AT_GetInt(_Camera.Feature.AOIWidth)
        self.aoiWidthChanged.emit(self._aoiWidth)
        return True


    @QtCore.pyqtProperty(_Camera.AuxiliaryOutSource, notify=auxiliaryOutSourceChanged)
    def auxiliaryOutSource(self):
        return self._auxiliaryOutSource

    @auxiliaryOutSource.setter
    def auxiliaryOutSource(self, auxiliaryOutSource):
        self._camera.auxiliaryOutSource = auxiliaryOutSource
        # Workaround for Andor bug (feature change callback for AuxiliaryOutSource is never called)
        self._auxiliaryOutSourceCb(_Camera.Feature.AuxiliaryOutSource)

    def _auxiliaryOutSourceCb(self, feature):
        self._auxiliaryOutSource = self._camera.auxiliaryOutSource
        self.auxiliaryOutSourceChanged.emit(self._auxiliaryOutSource)
        return True


    @QtCore.pyqtProperty(_Camera.Binning, notify=binningChanged)
    def binning(self):
        return self._binning

    @binning.setter
    def binning(self, binning):
        self._camera.binning = binning

    def _binningCb(self, feature):
        self._binning = self._camera.binning
        self.binningChanged.emit(self._binning)
        return True


    @QtCore.pyqtProperty(float, notify=bytesPerPixelChanged)
    def bytesPerPixel(self):
        return self._bytesPerPixel

    def _bytesPerPixelCb(self, feature):
        self._bytesPerPixel = self._camera.AT_GetFloat(_Camera.Feature.BytesPerPixel)
        self.bytesPerPixelChanged.emit(self._bytesPerPixel)
        return True


    @QtCore.pyqtProperty(_Camera.CycleMode, notify=cycleModeChanged)
    def cycleMode(self):
        return self._cycleMode

    @cycleMode.setter
    def cycleMode(self, cycleMode):
        self._camera.cycleMode = cycleMode

    def _cycleModeCb(self, feature):
        self._cycleMode = self._camera.cycleMode
        self.cycleModeChanged.emit(self._cycleMode)
        return True


    @QtCore.pyqtProperty(float, notify=exposureTimeChanged)
    def exposureTime(self):
        return self._exposureTime

    @exposureTime.setter
    def exposureTime(self, exposureTime):
        self._camera.AT_SetFloat(_Camera.Feature.ExposureTime, exposureTime)

    def _exposureTimeCb(self, feature):
        self._exposureTime = self._camera.AT_GetFloat(_Camera.Feature.ExposureTime)
        self.exposureTimeChanged.emit(self._exposureTime)
        return True


    @QtCore.pyqtProperty(_Camera.FanSpeed, notify=fanSpeedChanged)
    def fanSpeed(self):
        return self._fanSpeed

    @fanSpeed.setter
    def fanSpeed(self, fanSpeed):
        self._camera.fanSpeed = fanSpeed

    def _fanSpeedCb(self, feature):
        self._fanSpeed = self._camera.fanSpeed
        self.fanSpeedChanged.emit(self._fanSpeed)
        return True


    @QtCore.pyqtProperty(int, notify=frameCountChanged)
    def frameCount(self):
        return self._frameCount

    @frameCount.setter
    def frameCount(self, frameCount):
        self._camera.AT_SetInt(_Camera.Feature.FrameCount, frameCount)

    def _frameCountCb(self, feature):
        self._frameCount = self._camera.AT_GetInt(_Camera.Feature.FrameCount)
        self.frameCountChanged.emit(self._frameCount)
        return True


    @QtCore.pyqtProperty(float, notify=frameRateChanged)
    def frameRate(self):
        return self._frameRate

    @frameRate.setter
    def frameRate(self, frameRate):
        self._camera.AT_SetFloat(_Camera.Feature.FrameRate, frameRate)

    def _frameRateCb(self, feature):
        self._frameRate = self._camera.AT_GetFloat(_Camera.Feature.FrameRate)
        self.frameRateChanged.emit(self._frameRate)
        return True


    @QtCore.pyqtProperty(int, notify=imageSizeBytesChanged)
    def imageSizeBytes(self):
        return self._imageSizeBytes

    @imageSizeBytes.setter
    def imageSizeBytes(self, imageSizeBytes):
        self._camera.AT_SetInt(_Camera.Feature.ImageSizeBytes, imageSizeBytes)

    def _imageSizeBytesCb(self, feature):
        self._imageSizeBytes = self._camera.AT_GetInt(_Camera.Feature.ImageSizeBytes)
        self.imageSizeBytesChanged.emit(self._imageSizeBytes)
        return True


    @QtCore.pyqtProperty(bool, notify=ioInvertChanged)
    def ioInvert(self):
        return self._ioInvert

    @ioInvert.setter
    def ioInvert(self, ioInvert):
        self._camera.AT_SetBool(_Camera.Feature.IOInvert, ioInvert)

    def _ioInvertCb(self, feature):
        self._ioInvert = self._camera.AT_GetBool(_Camera.Feature.IOInvert)
        self.ioInvertChanged.emit(self._ioInvert)
        return True


    @QtCore.pyqtProperty(_Camera.IOSelector, notify=ioSelectorChanged)
    def ioSelector(self):
        return self._ioSelector

    @ioSelector.setter
    def ioSelector(self, ioSelector):
        self._camera.ioSelector = ioSelector

    def _ioSelectorCb(self, feature):
        self._ioSelector = self._camera.ioSelector
        self.ioSelectorChanged.emit(self._ioSelector)
        return True


    @QtCore.pyqtProperty(float, notify=maxInterfaceTransferRateChanged)
    def maxInterfaceTransferRate(self):
        return self._maxInterfaceTransferRate

    def _maxInterfaceTransferRateCb(self, feature):
        self._maxInterfaceTransferRate = self._camera.AT_GetFloat(_Camera.Feature.MaxInterfaceTransferRate)
        self.maxInterfaceTransferRateChanged.emit(self._maxInterfaceTransferRate)
        return True


    @QtCore.pyqtProperty(bool, notify=metadataEnabledChanged)
    def metadataEnabled(self):
        return self._metadataEnabled

    @metadataEnabled.setter
    def metadataEnabled(self, metadataEnabled):
        self._camera.AT_SetBool(_Camera.Feature.MetadataEnable, metadataEnabled)

    def _metadataEnabledCb(self, feature):
        self._metadataEnabled = self._camera.AT_GetBool(_Camera.Feature.MetadataEnable)
        self.metadataEnabledChanged.emit(self._metadataEnabled)
        return True


    @QtCore.pyqtProperty(bool, notify=metadataTimestampEnabledChanged)
    def metadataTimestampEnabled(self):
        return self._metadataTimestampEnabled

    @metadataTimestampEnabled.setter
    def metadataTimestampEnabled(self, metadataTimestampEnabled):
        self._camera.AT_SetBool(_Camera.Feature.MetadataTimestamp, metadataTimestampEnabled)

    def _metadataTimestampEnabledCb(self, Feature):
        self._metadataTimestampEnabled = self._camera.AT_GetBool(_Camera.Feature.MetadataTimestamp)
        self.metadataTimestampEnabledChanged.emit(self._metadataTimestampEnabled)
        return True


    @QtCore.pyqtProperty(bool, notify=overlapChanged)
    def overlap(self):
        return self._overlap

    @overlap.setter
    def overlap(self, overlap):
        self._camera.AT_SetBool(_Camera.Feature.Overlap, overlap)

    def _overlapCb(self, feature):
        self._overlap = self._camera.AT_GetBool(_Camera.Feature.Overlap)
        self.overlapChanged.emit(self._overlap)
        return True


    @QtCore.pyqtProperty(_Camera.PixelEncoding, notify=pixelEncodingChanged)
    def pixelEncoding(self):
        '''Note that PixelEncoding is not set directly; it depends upon the current value of SimplePreAmp.'''
        return self._pixelEncoding

    def _pixelEncodingCb(self, feature):
        self._pixelEncoding = self._camera.pixelEncoding
        self.pixelEncodingChanged.emit(self._pixelEncoding)
        return True


    @QtCore.pyqtProperty(_Camera.PixelReadoutRate, notify=pixelReadoutRateChanged)
    def pixelReadoutRate(self):
        return self._pixelReadoutRate

    @pixelReadoutRate.setter
    def pixelReadoutRate(self, pixelReadoutRate):
        self._camera.pixelReadoutRate = pixelReadoutRate

    def _pixelReadoutRateCb(self, feature):
        self._pixelReadoutRate = self._camera.pixelReadoutRate
        self.pixelReadoutRateChanged.emit(self._pixelReadoutRate)
        return True


    @QtCore.pyqtProperty(float, notify=readoutTimeChanged)
    def readoutTime(self):
        return self._readoutTime

    @readoutTime.setter
    def readoutTime(self, readoutTime):
        self._camera.AT_SetFloat(_Camera.Feature.ReadoutTime, readoutTime)

    def _readoutTimeCb(self, feature):
        self._readoutTime = self._camera.AT_GetFloat(_Camera.Feature.ReadoutTime)
        self.readoutTimeChanged.emit(self._readoutTime)
        return True


    @QtCore.pyqtProperty(bool, notify=sensorCoolingChanged)
    def sensorCooling(self):
        return self._sensorCooling

    @sensorCooling.setter
    def sensorCooling(self, sensorCooling):
        self._camera.AT_SetBool(_Camera.Feature.SensorCooling, sensorCooling)

    def _sensorCoolingCb(self, feature):
        self._sensorCooling = self._camera.AT_GetBool(_Camera.Feature.SensorCooling)
        self.sensorCoolingChanged.emit(self._sensorCooling)
        return True


    @QtCore.pyqtProperty(_Camera.Shutter, notify=shutterChanged)
    def shutter(self):
        return self._shutter

    @shutter.setter
    def shutter(self, shutter):
        self._camera.shutter = shutter

    def _shutterCb(self, feature):
        self._shutter = self._camera.shutter
        self.shutterChanged.emit(self._shutter)
        return True


    @QtCore.pyqtProperty(_Camera.SimplePreAmp, notify=simplePreAmpChanged)
    def simplePreAmp(self):
        return self._simplePreAmp

    @simplePreAmp.setter
    def simplePreAmp(self, simplePreAmp):
        self._camera.simplePreAmp = simplePreAmp

    def _simplePreAmpCb(self, feature):
        self._simplePreAmp = self._camera.simplePreAmp
        self.simplePreAmpChanged.emit(self._simplePreAmp)
        return True


    @QtCore.pyqtProperty(bool, notify=spuriousNoiseFilterChanged)
    def spuriousNoiseFilter(self):
        return self._spuriousNoiseFilter

    @spuriousNoiseFilter.setter
    def spuriousNoiseFilter(self, spuriousNoiseFilter):
        self._camera.AT_SetBool(_Camera.Feature.SpuriousNoiseFilter, spuriousNoiseFilter)

    def _spuriousNoiseFilterCb(self, feature):
        self._spuriousNoiseFilter = self._camera.AT_GetBool(_Camera.Feature.SpuriousNoiseFilter)
        self.spuriousNoiseFilterChanged.emit(self._spuriousNoiseFilter)
        return True


    @QtCore.pyqtProperty(int, notify=timestampClockFrequencyChanged)
    def timestampClockFrequency(self):
        return self._timestampClockFrequency

    @imageSizeBytes.setter
    def timestampClockFrequency(self, timestampClockFrequency):
        self._camera.AT_SetInt(_Camera.Feature.TimestampClockFrequency, timestampClockFrequency)

    def _timestampClockFrequencyCb(self, feature):
        self._timestampClockFrequency = self._camera.AT_GetInt(_Camera.Feature.TimestampClockFrequency)
        self.timestampClockFrequencyChanged.emit(self._timestampClockFrequency)
        return True


    @QtCore.pyqtProperty(_Camera.TriggerMode, notify=triggerModeChanged)
    def triggerMode(self):
        return self._triggerMode

    @triggerMode.setter
    def triggerMode(self, triggerMode):
        self._camera.triggerMode = triggerMode

    def _triggerModeCb(self, feature):
        self._triggerMode = self._camera.triggerMode
        self.triggerModeChanged.emit(self._triggerMode)
        return True


    @QtCore.pyqtProperty(tuple, notify=waitBufferTimeoutChanged)
    def waitBufferTimeout(self):
        return self._waitBufferTimeout

    @waitBufferTimeout.setter
    def waitBufferTimeout(self, waitBufferTimeout):
        if type(waitBufferTimeout) is Camera.WaitBufferTimeout and waitBufferTimeout == Camera.WaitBufferTimeout.Override or \
           waitBufferTimeout[0] == Camera.WaitBufferTimeout.Override and len(waitBufferTimeout) != 2:
            raise DeviceException(self, 'When setting the waitBufferTimeout property to Override, you must simultaneously ' +
                                        'specify the timeout value (in seconds) that you wish for AT_WaitBuffer to use. ' +
                                        'For example: "camera.waitBufferTimeout = (camera.WaitBufferTimeout.Override, 1.5)".')
        if type(waitBufferTimeout) is Camera.WaitBufferTimeout:
            waitBufferTimeout = (waitBufferTimeout,)
        elif waitBufferTimeout[0] != Camera.WaitBufferTimeout.Override:
            if len(waitBufferTimeout) != 1:
                raise DeviceException(self, 'When setting the waitBufferTimeout property to Default or Infinite, only one argument ' +
                                            'may be given.  For example: "camera.waitBufferTimeout = camera.WaitBufferTimeout.Default" ' +
                                            'or "camera.waitBufferTimeout = (camera.waitBufferTimeout.Default,)".')
            waitBufferTimeout = (waitBufferTimeout[0],)
        else:
            if waitBufferTimeout[1] < 0:
                raise DeviceException(self, 'waitBufferTimeout override value must be >= 0.')
            if waitBufferTimeout[1] > self._camera.Infinite / 1000:
                raise DeviceException(self, 'waitBufferTimeout override value must be <= {}.'.format(self._camera.Infinite / 1000))
            waitBufferTimeout = tuple(waitBufferTimeout)

        if waitBufferTimeout != self._waitBufferTimeout:
            self._waitBufferTimeout = waitBufferTimeout
            self.waitBufferTimeoutChanged.emit(self._waitBufferTimeout)


    def softwareTrigger(self):
        '''Send software trigger.  If the camera is in software triggered mode, an acquisition sequence has been started,
        and at least one suitable buffer has been queued, this will cause the camera to acquire a frame such that the current
        or next AT_WaitBuffer() completes once the frame has been transferred to the PC.'''
        if self.triggerMode != self.TriggerMode.Software:
            self._warn('Sending software trigger when not in software triggered exposure mode.')
        self._camera.AT_Command(self._camera.Feature.SoftwareTrigger)

    def getEnumStrings(self, feature):
        '''Returns a list of valid enum value names for the specified feature.  This will throw an exception if the specified
        feature does not represent an enumerated property (for example, because it is an int or float).'''
        return [self._camera.AT_GetEnumStringByIndex(feature, i) for i in range(self._camera.AT_GetEnumCount(feature))]

    def makeAcquisitionBuffer(self):
        '''Allocate and return a numpy ndarray to be used to AT_QueueBuffer(..).  Note that this function is extremely fast,
        requiring only 4.3 microseconds for a 16-bit 2560x2160 image.'''
        aoiStride = self._aoiStride
        imageBufferSize = self._imageSizeBytes
        if imageBufferSize <= 0:
            raise AndorException('ImageSizeBytes value last retrieved from Andor API is <= 0.')
        if imageBufferSize % aoiStride != 0:
            raise AndorException('Value of ImageSizeBytes last retrieved from Andor API is not divisible by AOIStride value.')
        return numpy.ndarray(shape=(imageBufferSize / aoiStride, aoiStride / 2), dtype=numpy.uint16, order='C')

    def acquireImage(self):
        '''This function grabs a single image by:
        * Flushing buffer queue
        * Setting camera to single frame, interally triggered
        * Queueing a single frame
        * Commanding acquisition sequence start
        * Waiting for the frame to be written to the buffer and handed back to us
        * Commanding acquisition sequence stop
        * Returning the acquired frame.'''
        imageBuffer = self.makeAcquisitionBuffer()

        self._camera.AT_Flush()
        if self.triggerMode != _Camera.TriggerMode.Internal:
            self.triggerMode = _Camera.TriggerMode.Internal
        if self.cycleMode != _Camera.CycleMode.Fixed:
            self.cycleMode = _Camera.CycleMode.Fixed
        if self.frameCount != 1:
            self.frameCount = 1

        # Queue acquisition buffer
        acquisitionTimeout = int(self._exposureTime * 3 * 1000)
        if acquisitionTimeout < 500:
            acquisitionTimeout = 500
        self._camera.AT_QueueBuffer(imageBuffer)

        # Initiate acquisition
        self._camera.AT_Command(self.Feature.AcquisitionStart)

        # Wait for acquisition to complete and verify that acquisition data was written to the acquisition buffer we queued
        acquiredBuffer = self._camera.AT_WaitBuffer(acquisitionTimeout)
        self._camera.AT_Command(self.Feature.AcquisitionStop)
        if acquiredBuffer != imageBuffer.ctypes.data_as(ctypes.c_void_p).value:
            raise AndorException('Acquired image buffer has different address than queued image buffer.')

        return imageBuffer[:self._aoiHeight, :self._aoiWidth]

    def startAcquisitionSequence(self):
        if self._acquisitionInitiatedByThisInstance or self._acquisitionSequenceInProgress:
            self._warn('Camera.startAcquisitionSequence(): Called while acquisition is already in progress.')
        else:
            self._camera.AT_Flush()
            self._acquisitionInitiatedByThisInstance = True
            self._queuedBuffers = {buffer.ctypes.data : buffer for buffer in [self.makeAcquisitionBuffer() for i in range(3)]}
            for buffer in self._queuedBuffers.values():
                self._camera.AT_QueueBuffer(buffer)
            self._camera.AT_Command(_Camera.Feature.AcquisitionStart)
            self._waitBuffer.emit()

    def stopAcquisitionSequence(self):
        self._acquisitionInitiatedByThisInstance = False
        self._camera.AT_Command(_Camera.Feature.AcquisitionStop)
        self._camera.AT_Flush()
        # Drop references to any queued buffers so that their backing buffers, so recently released from the Andor universe by
        # AT_Flush, may finally be deallocated
        self._queuedBuffers = {}

    def _waitBufferTimeoutValue(self):
        t = self._waitBufferTimeout[0]
        if t == Camera.WaitBufferTimeout.Infinite:
            return self._camera.Infinite
        if t == Camera.WaitBufferTimeout.Default:
            return max(500, int(self._exposureTime * 3 * 1000))
        if t == Camera.WaitBufferTimeout.Override:
            return int(1000 * self._waitBufferTimeout[1])
        raise DeviceError(self, 'A new value for WaitBufferTimeout was added without updating code that uses WaitBufferTimeout.')

    def _waitBufferSlot(self):
        if self._acquisitionInitiatedByThisInstance:
            voidp = self._camera.AT_WaitBuffer(self._waitBufferTimeoutValue())
            if voidp not in self._queuedBuffers:
                raise DeviceException(self, 'Acquired image buffer has different address than queued image buffer.')
            acquiredBuffer = self._queuedBuffers[voidp]
            del self._queuedBuffers[voidp]
            self.imageAcquired.emit(acquiredBuffer[:self._aoiHeight, :self._aoiWidth])
            if self._acquisitionInitiatedByThisInstance:
                newBuffer = self.makeAcquisitionBuffer()
                self._queuedBuffers[newBuffer.ctypes.data] = newBuffer
                self._camera.AT_QueueBuffer(newBuffer)
                self._waitBuffer.emit()

    QtCore.Q_ENUMS(AuxiliaryOutSource)
    QtCore.Q_ENUMS(Binning)
    QtCore.Q_ENUMS(CycleMode)
    QtCore.Q_ENUMS(FanSpeed)
    QtCore.Q_ENUMS(Feature)
    QtCore.Q_ENUMS(IOSelector)
    QtCore.Q_ENUMS(PixelEncoding)
    QtCore.Q_ENUMS(PixelReadoutRate)
    QtCore.Q_ENUMS(Shutter)
    QtCore.Q_ENUMS(SimplePreAmp)
    QtCore.Q_ENUMS(TemperatureStatus)
    QtCore.Q_ENUMS(TriggerMode)
