# Copyright 2014 WUSTL ZPLAB

import ctypes as ct
import numpy as np
from acquisition.andor.andor_exception import AndorException
from acquisition.andor._andor import _Camera
from acquisition.device import Device

class Camera(_Camera, Device):
    def __init__(self, deviceIndex, name='Andor Zyla 5.5'):
        _Camera.__init__(self, deviceIndex)
        Device.__init__(self, name)
        self._appendTypeName('Andor.Camera')

    def getPixelEncoding(self):
        enumIndex = self.AT_GetEnumIndex(self.Feature.PixelEncoding)
        return self.AT_GetEnumStringByIndex(self.Feature.PixelEncoding, enumIndex)

    def getEnumStrings(self, feature):
        return [self.AT_GetEnumStringByIndex(feature, i) for i in range(self.AT_GetEnumCount(feature))]

    def getEnumString(self, feature):
        return self.AT_GetEnumStringByIndex(feature, self.AT_GetEnumIndex(feature))

    def setExposureTime(self, exposureTime):
        '''Note that if exposureTime is less than the Camera's minimum exposure time as reported by the SDK, 
        then the minimum legal value is used.  Returns actual exposure time reported by SDK we set exposure time.'''
        minExposureTime = self.AT_GetFloatMin(self.Feature.ExposureTime)
        if exposureTime < minExposureTime:
            exposureTime = minExposureTime
        self.AT_SetFloat(self.Feature.ExposureTime, exposureTime)
        return self.AT_GetFloat(self.Feature.ExposureTime)

    def makeAcquisitionBuffer(self):
        aoiStride = self.AT_GetInt(self.Feature.AOIStride)
        imageBufferSize = self.AT_GetInt(self.Feature.ImageSizeBytes)
        if imageBufferSize <= 0:
            raise AndorException('ImageSizeBytes value retrieved from Andor API is <= 0.')
        if imageBufferSize % aoiStride != 0:
            raise AndorException('Value of ImageSizeBytes retrieved from Andor API is not divisible by AOIStride value.')
        return np.ndarray(shape=(imageBufferSize / aoiStride, aoiStride / 2), dtype=np.uint16, order='C')

    def acquireImage(self):
        imageBuffer = self.makeAcquisitionBuffer()

        # Queue acquisition buffer
        acquisitionTimeout = int(self.AT_GetFloat(self.Feature.ExposureTime) * 3 * 1000)
        if acquisitionTimeout < 500:
            acquisitionTimeout = 500
        self.AT_Flush()
        self.AT_QueueBuffer(imageBuffer)

        # Initiate acquisition
        self.AT_Command(self.Feature.AcquisitionStart)

        # Wait for acquisition to complete and verify that acquisition data was written to the acquisition buffer we queued
        acquiredBuffer = self.AT_WaitBuffer(acquisitionTimeout)
        self.AT_Command(self.Feature.AcquisitionStop)
        if acquiredBuffer != imageBuffer.ctypes.data_as(ct.c_void_p).value:
            raise AndorException('Acquired image buffer has different address than queued image buffer.')

        return imageBuffer[:self.AT_GetInt(self.Feature.AOIHeight), :self.AT_GetInt(self.Feature.AOIWidth)]

    @property
    def model(self):
        return self.AT_GetString(self.Feature.CameraModel)

    @property
    def acquiring(self):
        return self.AT_GetBool(self.Feature.CameraAcquiring)

    @property
    def exposureTime(self):
        return self.AT_GetFloat(self.Feature.ExposureTime)

    @exposureTime.setter
    def exposureTime(self, exposureTime):
        self.setExposureTime(exposureTime)

    @property
    def overlap(self):
        return self.AT_GetBool(self.Feature.Overlap)

    @overlap.setter
    def overlap(self, overlap):
        self.AT_SetBool(self.Feature.Overlap, overlap)

    @property
    def frameRate(self):
        return self.AT_GetFloat(self.Feature.FrameRate)

    @frameRate.setter
    def frameRate(self, frameRate):
        self.AT_SetFloat(self.Feature.FrameRate, frameRate)
