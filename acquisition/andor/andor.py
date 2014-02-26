# Copyright 2014 WUSTL ZPLAB

import ctypes as ct
import numpy as np
from acquisition.andor.andor_exception import AndorException
from acquisition.andor._andor import _Camera

class Camera(_Camera):
    def __init__(self, deviceIndex):
        super().__init__(deviceIndex)

    def getPixelEncoding(self):
        enumIndex = self.AT_GetEnumIndex(self.Feature.PixelEncoding)
        return self.AT_GetEnumStringByIndex(self.Feature.PixelEncoding, enumIndex)

    def acquireImage(self, exposureTime):
        # Exposure time
        self.AT_SetFloat(self.Feature.ExposureTime, exposureTime)

        # AOI binning
#        if self.andorInstance.atcore.AT_SetInt(self.deviceHandle, 'AOIHBin', 1) != 0:
#            raise AndorException('Failed to set horizontal binning.')
#        if self.andorInstance.atcore.AT_SetInt(self.deviceHandle, 'AOIVBin', 1) != 0:
#            raise AndorException('Failed to set vertical binning.')

        # AOI top left
        self.AT_SetInt(self.Feature.AOILeft, 1)
        self.AT_SetInt(self.Feature.AOITop, 1)

        # AOI width and height
        aoiw = self.AT_GetIntMax(self.Feature.AOIWidth)
        aoih = self.AT_GetIntMax(self.Feature.AOIHeight)
        self.AT_SetInt(self.Feature.AOIWidth, aoiw)
        self.AT_SetInt(self.Feature.AOIHeight, aoih)

        # AOI stride
        aoiStride = self.AT_GetInt(self.Feature.AOIStride)

        # Make acquisition buffer
        imageBufferSize = self.AT_GetInt(self.Feature.ImageSizeBytes)
        if imageBufferSize <= 0:
            raise AndorException('ImageSizeBytes value retrieved from Andor API is <= 0.')
        if imageBufferSize % aoiStride != 0:
            raise AndorException('Value of ImageSizeBytes retrieved from Andor API is not divisible by AOIStride value.')

        imageBuffer = np.ndarray(shape=(imageBufferSize / aoiStride, aoiStride / 2), dtype=np.uint16, order='C')

        # Queue acquisition buffer
        acquisitionTimeout = int(exposureTime * 3 * 1000)
        if acquisitionTimeout < 500:
            acquisitionTimeout = 500
        self.AT_Flush()
        self.AT_QueueBuffer(imageBuffer)

        # Initiate acquisition
        self.AT_Command(self.Feature.AcquisitionStart)

        # Wait for acquisition to complete and verify that acquisition data was written to the acquisition buffer we queued
        acquiredBuffer = self.AT_WaitBuffer(acquisitionTimeout)
        if acquiredBuffer != imageBuffer.ctypes.data_as(ct.c_void_p).value:
            raise AndorException('Acquired image buffer has different address than queued image buffer.')

        return imageBuffer[:aoih, :aoiw]
