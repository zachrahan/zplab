# Copyright 2014 WUSTL ZPLAB

import ctypes
import numpy
import threading
from PyQt5 import QtCore
from acquisition.andor.andor_exception import AndorException
from acquisition.andor._andor import _Camera
from acquisition.device import Device, DeviceException, ThreadedDevice, ThreadedDeviceWorker

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

    There is generally a 1:1 mapping between properties presented by this class and Andor feature names described
    in the Andor SDK reference.  However, this is not the case for IO inversion, which this class abstracts.  In detail,
    the Andor API allows selection of which pin to invert (IOSelector feature) and provides for toggling whether the
    selected pin is inverted (IOInvert feature).  This presents IO inversion through the property ioInversion as a dict
    mapping pin enum value to inversion state, eg: {Camera.IOSelector.Fire1 : True, Camera.IOSelector.FireN : False, ...}

    Note that for this device, the device thread is used only for AT_WaitBuffer() calls.'''

    @staticmethod
    def getDeviceNames():
        '''This function makes Andor API calls that tend to run slowly and so can take a second or two to complete.'''
        return list(_Camera.getDeviceNames())

    AuxiliaryOutSource = _Camera.AuxiliaryOutSource
    Binning = _Camera.Binning
    CycleMode = _Camera.CycleMode
    FanSpeed = _Camera.FanSpeed
    Feature = _Camera.Feature
    IOSelector = _Camera.IOSelector
    PixelEncoding = _Camera.PixelEncoding
    Shutter = _Camera.Shutter
    SimplePreAmp = _Camera.SimplePreAmp
    TemperatureStatus = _Camera.TemperatureStatus
    TriggerMode = _Camera.TriggerMode

    # Much of the following code could be auto-generated at run time and, in fact, initially was.  However, it was tricky understand
    # and trickier still to debug.

    accumulateCountChanged = QtCore.pyqtSignal(int)
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
    ioInversionChanged = QtCore.pyqtSignal(dict)
    maxInterfaceTransferRateChanged = QtCore.pyqtSignal(float)
    metadataEnabledChanged = QtCore.pyqtSignal(bool)
    metadataTimestampEnabledChanged = QtCore.pyqtSignal(bool)
    overlapChanged = QtCore.pyqtSignal(bool)
    pixelEncodingChanged = QtCore.pyqtSignal(_Camera.PixelEncoding)
    readoutTimeChanged = QtCore.pyqtSignal(float)
    sensorCoolingChanged = QtCore.pyqtSignal(bool)
    shutterChanged = QtCore.pyqtSignal(_Camera.Shutter)
    simplePreAmpChanged = QtCore.pyqtSignal(_Camera.SimplePreAmp)
    spuriousNoiseFilterChanged = QtCore.pyqtSignal(bool)
    timestampClockFrequencyChanged = QtCore.pyqtSignal(int)
    triggerModeChanged = QtCore.pyqtSignal(_Camera.TriggerMode)

    def __init__(self, parent=None, deviceName='Andor Zyla 5.5', andorDeviceIndex=0):
        '''Note: The deviceName argument sets the .deviceName property; it does not act as a criterion for choosing which Andor camera 
        to open.  That is controlled by the andorDeviceIndex argument exclusively.'''
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
            self._ioInversion = {}
            for pin in _Camera.IOSelector.values.values():
                self._camera.ioSelector = pin
                self._ioInversion[pin] = self._camera.AT_GetBool(_Camera.Feature.IOInvert)
            self._inverting = False
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

    def __del__(self):
        with self._cmdLock:
            for crt in self._callbackTokens:
                self._camera.AT_UnregisterFeatureCallback(crt)
            self._callbackTokens = []
            try:
                # Attempt to stop acquisition in case device thread is blocking on AT_WaitBuffer(..) that would never
                # otherwise complete
                self._camera.AT_Command(self.Feature.AcquisitionStop)
            except AndorException as e:
                pass
        ThreadedDevice.__del__(self)


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


    @QtCore.pyqtProperty(str)
    def serialNumber(self):
        return self._serialNumber


    @QtCore.pyqtProperty(float)
    def sensorTemperature(self):
        '''Sensor temperature may change at any time, and the Andor SDK has no mechanism for notifying us when it has,
        so every get of this property causes the current value to be retrieved from the camera and returned.'''
        with self._cmdLock:
            return self._camera.AT_GetFloat(_Camera.Feature.SensorTemperature)


    @QtCore.pyqtProperty(int)
    def timestampClock(self):
        '''As with sensorTemperature, this property's value is not cached and each read causes the current value to be
        retrieved from the camera.'''
        with self._cmdLock:
            return self._camera.AT_GetInt(_Camera.Feature.TimestampClock)


    @QtCore.pyqtProperty(int, notify=accumulateCountChanged)
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
        return True


    @QtCore.pyqtProperty(int, notify=aoiHeightChanged)
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
        return True


    @QtCore.pyqtProperty(int, notify=aoiLeftChanged)
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
        return True


    @QtCore.pyqtProperty(int, notify=aoiStrideChanged)
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
        return True


    @QtCore.pyqtProperty(int, notify=aoiTopChanged)
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
        return True


    @QtCore.pyqtProperty(int, notify=aoiWidthChanged)
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
        return True


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
        return True


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
        return True


    @QtCore.pyqtProperty(float, notify=bytesPerPixelChanged)
    def bytesPerPixel(self):
        with self._propLock:
            return self._bytesPerPixel

    def _bytesPerPixelCb(self, feature):
        with self._propLock, self._cmdLock:
            self._bytesPerPixel = self._camera.AT_GetFloat(_Camera.Feature.BytesPerPixel)
            self.bytesPerPixelChanged.emit(self._bytesPerPixel)
        return True


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
        return True


    @QtCore.pyqtProperty(float, notify=exposureTimeChanged)
    def exposureTime(self):
        with self._propLock:
            return self._exposureTime

    @exposureTime.setter
    def exposureTime(self, exposureTime):
        with self._cmdLock:
            self._camera.AT_SetFloat(_Camera.Feature.ExposureTime, exposureTime)

    def _exposureTimeCb(self, feature):
        with self._propLock, self._cmdLock:
            self._exposureTime = self._camera.AT_GetFloat(_Camera.Feature.ExposureTime)
            self.exposureTimeChanged.emit(self._exposureTime)
        return True


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
        return True


    @QtCore.pyqtProperty(int, notify=frameCountChanged)
    def frameCount(self):
        with self._propLock:
            return self._frameCount

    @frameCount.setter
    def frameCount(self, frameCount):
        with self._cmdLock:
            self._camera.AT_SetInt(_Camera.Feature.FrameCount, frameCount)

    def _frameCountCb(self, feature):
        with self._propLock, self._cmdLock:
            self._frameCount = self._camera.AT_GetInt(_Camera.Feature.FrameCount)
            self.frameCountChanged.emit(self._frameCount)
        return True


    @QtCore.pyqtProperty(float, notify=frameRateChanged)
    def frameRate(self):
        with self._propLock:
            return self._frameRate

    @frameRate.setter
    def frameRate(self, frameRate):
        with self._cmdLock:
            self._camera.AT_SetFloat(_Camera.Feature.FrameRate, frameRate)

    def _frameRateCb(self, feature):
        with self._propLock, self._cmdLock:
            self._frameRate = self._camera.AT_GetFloat(_Camera.Feature.FrameRate)
            self.frameRateChanged.emit(self._frameRate)
        return True


    @QtCore.pyqtProperty(int, notify=imageSizeBytesChanged)
    def imageSizeBytes(self):
        with self._propLock:
            return self._imageSizeBytes

    @imageSizeBytes.setter
    def imageSizeBytes(self, imageSizeBytes):
        with self._cmdLock:
            self._camera.AT_SetInt(_Camera.Feature.ImageSizeBytes, imageSizeBytes)

    def _imageSizeBytesCb(self, feature):
        with self._propLock, self._cmdLock:
            self._imageSizeBytes = self._camera.AT_GetInt(_Camera.Feature.ImageSizeBytes)
            self.imageSizeBytesChanged.emit(self._imageSizeBytes)
        return True


    @QtCore.pyqtProperty(dict, notify=ioInversionChanged)
    def ioInversion(self):
        with self._propLock:
            return self._ioInversion.copy()

    @ioInversion.setter
    def ioInversion(self, ioInversion):
        with self._propLock:
            modified = False
            with self._cmdLock:
                self._inverting = True
                for ios, newIoi in ioInversion.items():
                    curIoi = self._ioInversion[ios]
                    if curIoi != newIoi:
                        if self._ioSelector != ios:
                            self._camera.ioSelector = ios
                            self._ioSelector = ios
                        self._camera.AT_SetBool(_Camera.Feature.IOInvert, newIoi)
                        self._ioInversion[ios] = newIoi
                        modified = True
                self._inverting = False
            if modified:
                self.ioInversionChanged.emit(self._ioInversion.copy())

    def _ioInvertCb(self, feature):
        if not self._inverting:
            with self._propLock, self._cmdLock:
                curIoi = self._ioInversion[self._ioSelector]
                newIoi = self._camera.AT_GetBool(_Camera.Feature.IOInvert)
                if curIoi != newIoi:
                    self._ioInversion[self._ioSelector] = newIoi
                    self.ioInversionChanged.emit(self._ioInversion.copy())
        return True

    def _ioSelectorCb(self, feature):
        if not self._inverting:
            with self._propLock, self._cmdLock:
                self._ioSelector = self._camera.ioSelector
        return True


    @QtCore.pyqtProperty(float, notify=maxInterfaceTransferRateChanged)
    def maxInterfaceTransferRate(self):
        with self._propLock:
            return self._maxInterfaceTransferRate

    def _maxInterfaceTransferRateCb(self, feature):
        with self._propLock, self._cmdLock:
            self._maxInterfaceTransferRate = self._camera.AT_GetFloat(_Camera.Feature.MaxInterfaceTransferRate)
            self.maxInterfaceTransferRateChanged.emit(self._maxInterfaceTransferRate)
        return True


    @QtCore.pyqtProperty(bool, notify=metadataEnabledChanged)
    def metadataEnabled(self):
        with self._propLock:
            return self._metadataEnabled

    @metadataEnabled.setter
    def metadataEnabled(self, metadataEnabled):
        with self._cmdLock:
            self._camera.AT_SetBool(_Camera.Feature.MetadataEnable, metadataEnabled)

    def _metadataEnabledCb(self, feature):
        with self._propLock, self.cmdLock:
            self._metadataEnabled = self._camera.AT_GetBool(_Camera.Feature.MetadataEnable)
            self.metadataEnabledChanged.emit(self._metadataEnabled)
        return True


    @QtCore.pyqtProperty(bool, notify=metadataTimestampEnabledChanged)
    def metadataTimestampEnabled(self):
        with self._propLock:
            return self._metadataTimestampEnabled

    @metadataTimestampEnabled.setter
    def metadataTimestampEnabled(self, metadataTimestampEnabled):
        with self._cmdLock:
            self._camera.AT_SetBool(_Camera.Feature.MetadataTimestamp, metadataTimestampEnabled)

    def _metadataTimestampEnabledCb(self, Feature):
        with self._propLock, self._cmdLock:
            self._metadataTimestampEnabled = self._camera.AT_GetBool(_Camera.Feature.MetadataTimestamp)
            self.metadataTimestampEnabledChanged.emit(self._metadataTimestampEnabled)
        return True


    @QtCore.pyqtProperty(bool, notify=overlapChanged)
    def overlap(self):
        with self._propLock:
            return self._overlap

    @overlap.setter
    def overlap(self, overlap):
        with self._cmdLock:
            self._camera.AT_SetBool(_Camera.Feature.Overlap, overlap)

    def _overlapCb(self, feature):
        with self._propLock, self._cmdLock:
            self._overlap = self._camera.AT_GetBool(_Camera.Feature.Overlap)
            self.overlapChanged.emit(self._overlap)
        return True


    @QtCore.pyqtProperty(_Camera.PixelEncoding, notify=pixelEncodingChanged)
    def pixelEncoding(self):
        '''Note that PixelEncoding is not set directly; it depends upon the current value of SimplePreAmp.'''
        with self._propLock:
            return self._pixelEncoding

    def _pixelEncodingCb(self, feature):
        with self._propLock, self._cmdLock:
            self._pixelEncoding = self._camera.pixelEncoding
            self.pixelEncodingChanged.emit(self._pixelEncoding)
        return True


    @QtCore.pyqtProperty(float, notify=readoutTimeChanged)
    def readoutTime(self):
        with self._propLock:
            return self._readoutTime

    @readoutTime.setter
    def readoutTime(self, readoutTime):
        with self._cmdLock:
            self._camera.AT_SetFloat(_Camera.Feature.ReadoutTime, readoutTime)

    def _readoutTimeCb(self, feature):
        with self._propLock, self._cmdLock:
            self._readoutTime = self._camera.AT_GetFloat(_Camera.Feature.ReadoutTime)
            self.readoutTimeChanged.emit(self._readoutTime)
        return True


    @QtCore.pyqtProperty(bool, notify=sensorCoolingChanged)
    def sensorCooling(self):
        with self._propLock:
            return self._sensorCooling

    @sensorCooling.setter
    def sensorCooling(self, sensorCooling):
        with self._cmdLock:
            self._camera.AT_SetBool(_Camera.Feature.SensorCooling, sensorCooling)

    def _sensorCoolingCb(self, feature):
        with self._propLock, self._cmdLock:
            self._sensorCooling = self._camera.AT_GetBool(_Camera.Feature.SensorCooling)
            self.sensorCoolingChanged.emit(self._sensorCooling)
        return True


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
        return True


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
        return True


    @QtCore.pyqtProperty(bool, notify=spuriousNoiseFilterChanged)
    def spuriousNoiseFilter(self):
        with self._propLock:
            return self._spuriousNoiseFilter

    @spuriousNoiseFilter.setter
    def spuriousNoiseFilter(self, spuriousNoiseFilter):
        with self._cmdLock:
            self._camera.AT_SetBool(_Camera.Feature.SpuriousNoiseFilter, spuriousNoiseFilter)

    def _spuriousNoiseFilterCb(self, feature):
        with self._propLock, self._cmdLock:
            self._spuriousNoiseFilter = self._camera.AT_GetBool(_Camera.Feature.SpuriousNoiseFilter)
            self.spuriousNoiseFilterChanged.emit(self._spuriousNoiseFilter)
        return True


    @QtCore.pyqtProperty(int, notify=timestampClockFrequencyChanged)
    def timestampClockFrequency(self):
        with self._propLock:
            return self._timestampClockFrequency

    @imageSizeBytes.setter
    def timestampClockFrequency(self, timestampClockFrequency):
        with self._cmdLock:
            self._camera.AT_SetInt(_Camera.Feature.TimestampClockFrequency, timestampClockFrequency)

    def _timestampClockFrequencyCb(self, feature):
        with self._propLock, self._cmdLock:
            self._timestampClockFrequency = self._camera.AT_GetInt(_Camera.Feature.TimestampClockFrequency)
            self.timestampClockFrequencyChanged.emit(self._timestampClockFrequency)
        return True


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
        return True


    def getEnumStrings(self, feature):
        return [self._camera.AT_GetEnumStringByIndex(feature, i) for i in range(self._camera.AT_GetEnumCount(feature))]

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

    QtCore.Q_ENUMS(AuxiliaryOutSource)
    QtCore.Q_ENUMS(Binning)
    QtCore.Q_ENUMS(CycleMode)
    QtCore.Q_ENUMS(FanSpeed)
    QtCore.Q_ENUMS(Feature)
#   QtCore.Q_ENUMS(IOSelector)
    QtCore.Q_ENUMS(PixelEncoding)
    QtCore.Q_ENUMS(Shutter)
    QtCore.Q_ENUMS(SimplePreAmp)
    QtCore.Q_ENUMS(TemperatureStatus)
    QtCore.Q_ENUMS(TriggerMode)

class _CameraWorker(ThreadedDeviceWorker):
    def __init__(self, device):
        super().__init__(device)

