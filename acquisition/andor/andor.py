# Copyright 2014 WUSTL ZPLAB

import ctypes
import numpy
from acquisition.andor.andor_exception import AndorException

class Andor:
    def __init__(self):
        self.atcore = ctypes.CDLL('libatcore.so')
        self.atcore.AT_InitialiseLibrary()

    def __del__(self):
        self.atcore.AT_FinaliseLibrary()

    def getDeviceNames(self):
        deviceNames = []
        deviceCount = ctypes.c_longlong(-1)
        self.atcore.AT_GetInt(1, ctypes.c_wchar_p('Device Count'), ctypes.byref(deviceCount))
        handle = ctypes.c_int(-1);
        deviceName = ctypes.create_unicode_buffer(128)
        for deviceIndex in range(deviceCount.value):
            self.atcore.AT_Open(deviceIndex, ctypes.byref(handle))
            self.atcore.AT_GetString(handle, ctypes.c_wchar_p('Camera Model'), deviceName, 128)
            deviceNames.append(deviceName.value)
            self.atcore.AT_Close(handle)
        return deviceNames
