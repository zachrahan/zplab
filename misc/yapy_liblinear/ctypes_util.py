import ctypes
import sys
import os

lib_dirs = (
  '/lib',
  '/usr/lib',
  '/usr/lib64',
  '/usr/local/lib',
  '/opt/local/lib',
  )

def register_api(lib, api):
  for f, (restype, argtypes) in api.iteritems():
    func = getattr(lib, f)
    func.restype = restype
    func.argtypes = argtypes

def load_library(dirs=(), *libnames):
  lib = None
  for d in list(dirs)+list(lib_dirs):
    for libname in libnames:
      lib = load_library_from_path(libname, d)
      if lib:
        return lib
  raise OSError("Could not load library.")

def load_library_from_path(libname, loader_path, dlltype=None):
  ext = os.path.splitext(libname)[1]

  if not ext:
    libname_ext = ['%s.so' % libname, '%s.pyd' % libname]
    if sys.platform == 'win32':
      libname_ext.insert(0, '%s.dll' % libname)
    elif sys.platform == 'darwin':
      libname_ext.insert(0, '%s.dylib' % libname)
    else:
      libname_ext.insert(0, '%s.so' % libname)
  else:
    libname_ext = [libname]

  loader_path = os.path.abspath(loader_path)
  if dlltype is None:
    if sys.platform == 'win32':
      dlltype = ctypes.WinDLL
    else:
      dlltype = ctypes.CDLL
  if not os.path.isdir(loader_path):
    libdir = os.path.dirname(loader_path)
  else:
    libdir = loader_path

  for ln in libname_ext:
    try:
      libpath = os.path.join(libdir, ln)
      return dlltype(libpath)
    except OSError as e:
      pass

