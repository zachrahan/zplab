
from acquisition.andor.andor import Camera
import time

c = Camera(0)
c.AT_SetBool(c.Feature.Overlap, False)
c.AT_SetEnumString(c.Feature.TriggerMode, 'Internal')
c.AT_SetEnumString(c.Feature.CycleMode, 'Fixed')
c.AT_SetInt(c.Feature.FrameCount, 1000)
c.AT_SetEnumString(c.Feature.SimplePreAmpGainControl, '12-bit (low noise)')
c.AT_SetEnumString(c.Feature.PixelEncoding, 'Mono12')
c.AT_SetFloat(c.Feature.ExposureTime, 0.001)
print(c.AT_GetFloat(c.Feature.ExposureTime))

def test():
    buffer = c.makeAcquisitionBuffer()
    for i in range(1000):
        c.AT_QueueBuffer(buffer)
    i = 0
    c.AT_Command(c.Feature.AcquisitionStart)
    try:
        while True:
            buffer.fill(0)
            t = time.time()
            out = c.AT_WaitBuffer(2000)
            assert(out == buffer.ctypes.data)
            assert((buffer != 0).any())
            t = time.time() - t
            print(i, t*1000, 1/t)
            i += 1

    finally:
        c.AT_Command(c.Feature.AcquisitionStop)
        c.AT_Flush()

