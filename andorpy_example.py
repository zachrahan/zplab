#!/usr/bin/env python3

from acquisition.andor.andor import Camera
import numpy as np
import ctypes as ct

# List the currently attached devices
print(list(Camera.getDeviceNames()))

# Open the camera at index 0.  This is the camera first in the list we just printed.
c = Camera(0)

# Print out some info.  Note that, in IPython, pressing tab will complete / offer all relevant choices for Camera.Feature...
# Note that all SDK functions are wrapped and do not return error codes - SDK error codes are translated into exceptions
# that are thrown in C++ and translated into Python AndorExceptions.
print('AOI: {} {}'.format(c.AT_GetInt(c.Feature.AOIWidth), c.AT_GetInt(c.Feature.AOIHeight)))

# Disable overlapped mode
c.AT_SetBool(c.Feature.Overlap, False)

# Print the different choices available for an SDK enum
print(c.getEnumStrings(c.Feature.ElectronicShutteringMode))

# Set an SDK enum by string
c.AT_SetEnumString(c.Feature.ElectronicShutteringMode, "Global")

# Print the current value of an enum by string
print(c.getEnumString(c.Feature.ElectronicShutteringMode))

# BitDepth is not set directly but is instead modified as a consequence of setting SimplePreAmpGainControl
print(c.getEnumStrings(c.Feature.SimplePreAmpGainControl))
c.AT_SetEnumString(c.Feature.SimplePreAmpGainControl, '16-bit (low noise & high well capacity)')
print('Bit depth: {}.'.format(c.getEnumString(c.Feature.BitDepth)))

# Set exposure to minimum value
c.AT_SetFloat(c.Feature.ExposureTime, c.AT_GetFloat(c.Feature.ExposureTime))
print('Exposure set to {} seconds.'.format(c.AT_GetFloat(c.Feature.ExposureTime)))



# Acquire a single image the easy way.  It could be easier: right now, it assumes the camera is
# already in fixed & internal modes with framecount 1.
c.AT_SetEnumString(c.Feature.CycleMode, 'Fixed')
c.AT_SetEnumString(c.Feature.TriggerMode, 'Internal')
c.AT_SetInt(c.Feature.FrameCount, 1)
an_image = c.acquireImage()
c.AT_Flush()



# Acquire a series of images in overlapped mode...
c.AT_SetEnumString(c.Feature.CycleMode, 'Fixed')
c.AT_SetEnumString(c.Feature.TriggerMode, 'Internal')
c.AT_SetBool(c.Feature.Overlap, True)
c.AT_SetInt(c.Feature.FrameCount, 10)

# Make some buffers.  The buffers are suited to the current state of the Camera - ie, 
# big enough to hold an image at the current bit depth and for the current resolution,
# plus an extra image row for metadata if enabled.
buffers = [c.makeAcquisitionBuffer() for x in range(10)]

# Queue them
for buffer in buffers:
    c.AT_QueueBuffer(buffer)

# Start acquisition
c.AT_Command(c.Feature.AcquisitionStart)

# Dequeue buffers, verifying that they came back in the expected order, with a timeout of one hundred seconds for each wait
for buffer in buffers:
    abuffer = c.AT_WaitBuffer(100 * 1000)
    if abuffer != buffer.ctypes.data_as(ct.c_void_p).value:
        print("wanted {} got {}.".format(abuffer, buffer.ctypes.data_as(ct.c_void_p).value))
    else:
        print("ok")

c.AT_Command(c.Feature.AcquisitionStop)
