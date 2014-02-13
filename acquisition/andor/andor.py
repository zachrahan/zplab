# Copyright 2014 WUSTL ZPLAB

import ctypes as ct
import numpy as np
from acquisition.andor.andor_exception import AndorException

class Andor:
    def __init__(self):
        self.atcore = ct.CDLL('libatcore.so')
        self.atcore.AT_InitialiseLibrary()

    def __del__(self):
        self.atcore.AT_FinaliseLibrary()

    def getDeviceNames(self):
        deviceNames = []
        deviceCount = ct.c_longlong(-1)
        self.atcore.AT_GetInt(1, 'Device Count', ct.byref(deviceCount))
        handle = ct.c_int(-1);
        deviceName = ct.create_unicode_buffer(128)
        for deviceIndex in range(deviceCount.value):
            self.atcore.AT_Open(deviceIndex, ct.byref(handle))
            self.atcore.AT_GetString(handle, 'Camera Model', deviceName, 128)
            deviceNames.append(deviceName.value)
            self.atcore.AT_Close(handle)
        return deviceNames

class Zyla:
    def __init__(self, andorInstance, deviceIndex):
        self.andorInstance = andorInstance
        self.deviceHandle = ct.c_int(-1)
        self.isOpen = False
        if self.andorInstance.atcore.AT_Open(deviceIndex, ct.byref(self.deviceHandle)) != 0:
            raise AndorException('AT_Open(..) failed.')
        self.isOpen = True

    def __del__(self):
        if self.isOpen:
            self.andorInstance.atcore.AT_Close(self.deviceHandle)

    def getPixelEncoding(self):
        enumIndex = ct.c_int(-1)
        if self.andorInstance.atcore.AT_GetEnumIndex(self.deviceHandle, 'PixelEncoding', ct.byref(enumIndex)) != 0:
            raise AndorException('AT_GetEnumIndex(..) for PixelEncoding failed.')
        pixelEncoding = ct.create_unicode_buffer(128)
        if self.andorInstance.atcore.AT_GetEnumStringByIndex(self.deviceHandle, 'PixelEncoding', enumIndex, pixelEncoding, 128) != 0:
            raise AndorException('AT_GetEnumStringByIndex(..) for PixelEncoding failed.')
        return pixelEncoding.value

    def acquireImage(self, exposureTime):
        # Exposure time
        if self.andorInstance.atcore.AT_SetFloat(self.deviceHandle, 'Exposure Time', ct.c_double(exposureTime)) != 0:
            raise AndorException('Failed to set exposure time.')

        # AOI binning
#        if self.andorInstance.atcore.AT_SetInt(self.deviceHandle, 'AOIHBin', 1) != 0:
#            raise AndorException('Failed to set horizontal binning.')
#        if self.andorInstance.atcore.AT_SetInt(self.deviceHandle, 'AOIVBin', 1) != 0:
#            raise AndorException('Failed to set vertical binning.')

        # AOI top left
        if self.andorInstance.atcore.AT_SetInt(self.deviceHandle, 'AOILeft', 1) != 0:
            raise AndorException('Failed to set AOI left.')
        if self.andorInstance.atcore.AT_SetInt(self.deviceHandle, 'AOITop', 1) != 0:
            raise AndorException('Failed to set AOI top.')

        # AOI width and height
        aoiw = ct.c_longlong(-1)
        if self.andorInstance.atcore.AT_GetIntMax(self.deviceHandle, 'AOI Width', ct.byref(aoiw)) != 0:
            raise AndorException('Failed to get max AOI width.')
        if self.andorInstance.atcore.AT_SetInt(self.deviceHandle, 'AOI Width', aoiw) != 0:
            raise AndorException('Failed to set AOI width to maximum ({}).'.format(aoiw.value))
        aoih = ct.c_longlong(-1)
        if self.andorInstance.atcore.AT_GetIntMax(self.deviceHandle, 'AOI Height', ct.byref(aoih)) != 0:
            raise AndorException('Failed to get max AOI height.')
        if self.andorInstance.atcore.AT_SetInt(self.deviceHandle, 'AOI Height', aoih) != 0:
            raise AndorException('Failed to set AOI height to maximum ({}).'.format(aoih.value))

        aoiStride = ct.c_longlong(-1)
        if self.andorInstance.atcore.AT_GetInt(self.deviceHandle, 'AOIStride', ct.byref(aoiStride)) != 0:
            raise AndorException('Failed to get AOI stride.')

        imageBufferSize = ct.c_longlong(-1)
        if self.andorInstance.atcore.AT_GetInt(self.deviceHandle, 'ImageSizeBytes', ct.byref(imageBufferSize)) != 0:
            raise AndorException('Failed to get ImageSizeBytes.')
        if imageBufferSize.value <= 0:
            raise AndorException('ImageSizeBytes value retrieved from Andor API is <= 0.')
        if imageBufferSize.value % aoiStride.value != 0:
            raise AndorException('Value of ImageSizeBytes retrieved from Andor API is not divisible by AOIStride value.')

        imageBuffer = np.ndarray(shape=(imageBufferSize.value / aoiStride.value, aoiStride.value / 2), dtype=np.uint16, order='C')

        acquisitionTimeout = int(exposureTime * 3 * 1000)
        if acquisitionTimeout < 500:
            acquisitionTimeout = 500
        if self.andorInstance.atcore.AT_QueueBuffer(self.deviceHandle, imageBuffer.ctypes.data_as(ct.POINTER(ct.c_ubyte)), imageBufferSize) != 0:
            raise AndorException('Failed to queue image buffer for acquisition from camera.')
        print(self.andorInstance.atcore.AT_Command(self.deviceHandle, 'Acquisition Start'))
#        if self.andorInstance.atcore.AT_Command(self.deviceHandle, 'AcquisitionStart') != 0:
#            raise AndorException('Acquisition start command failed.')
        acquiredBuffer = ct.c_void_p()
        acquiredBufferSize = ct.c_longlong(-1);
        print(self.andorInstance.atcore.AT_WaitBuffer(self.deviceHandle, ct.byref(acquiredBuffer), ct.byref(acquiredBufferSize), acquisitionTimeout))
#           raise AndorException('Failed to acquire buffer from camera.')
