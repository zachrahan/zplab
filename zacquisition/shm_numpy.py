# The MIT License (MIT)
#
# Copyright (c) 2014 WUSTL ZPLAB
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#
# Authors: Erik Hvatum

import ctypes
import errno
import numpy

libc = ctypes.CDLL('libc.so.6')
librt = ctypes.CDLL('librt.so.1')

librt.shm_open.argtypes = [ctypes.c_char_p, ctypes.c_int, ctypes.c_uint32]
librt.shm_unlink.argtypes = [ctypes.c_char_p]

libc.ftruncate.argtypes = [ctypes.c_int, ctypes.c_int64]
libc.mmap.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int64]
libc.mmap.restype = ctypes.c_void_p
libc.munmap.argtypes = [ctypes.c_void_p, ctypes.c_size_t]
libc.close.argtypes = [ctypes.c_int]

O_RDONLY = 0
O_RDWR   = 2
O_CREAT  = 64
O_EXCL   = 128
O_TRUNC  = 512
PROT_READ  = 1
PROT_WRITE = 2
MAP_SHARED = 1
MAP_FAILED = ctypes.cast(-1, ctypes.c_void_p)
c_uint16_p = ctypes.POINTER(ctypes.c_uint16)

class SharedMem:
    def __init__(self, name, shape, create=True, own=True):
        self.own = own
        self.fd = None
        self.data = None
        self.name = name.encode('utf-8') if type(name) is str else name
        self.byteCount = numpy.array(shape).prod() * 2
        self.ndarray = None
        if create:
            # NB: 0o600 represents the unix permission value readable/writeable by owner
            self.fd = librt.shm_open(self.name, O_RDWR | O_CREAT | O_EXCL, 0o600)
            if self.fd == -1:
                self._rose('libc.shm_open')
            if libc.ftruncate(self.fd, self.byteCount) == -1:
                self._rose('libc.ftruncate')
        else:
            self.fd = librt.shm_open(self.name, O_RDWR, 0)
            if self.fd == -1:
                self._rose('libc.shm_open')
        data = libc.mmap(ctypes.c_void_p(0), self.byteCount, PROT_READ | PROT_WRITE, MAP_SHARED, self.fd, 0)
        if data == MAP_FAILED or data == ctypes.c_void_p(0):
            self._rose('libc.mmap')
        self.data = ctypes.cast(data, c_uint16_p)
        self.ndarray = numpy.ctypeslib.as_array(self.data, shape)

    def __del__(self):
        del self.ndarray
        if self.data is not None:
            libc.munmap(ctypes.cast(self.data, ctypes.c_void_p), self.byteCount)
        if self.fd is not None:
            if libc.close(self.fd) == -1:
                self._rose('libc.close')
            if self.own:
                if librt.shm_unlink(self.name) == -1:
                    self._rose('librt.shm_unlink')

    @staticmethod
    def _rose(fname):
        e = ctypes.get_errno()
        if e == 0:
            raise RuntimeError(fname + ' failed, but errno is 0.')
        raise OSError(e, errno.errorcode.get(e, 'UNKNOWN ERROR'))
