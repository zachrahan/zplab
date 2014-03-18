#!/usr/bin/env bash

PYTHONPATH=/mnt/scopearray/mm/micro-manager/MMCorePy_wrap/build/lib.linux-x86_64-3.3 LD_LIBRARY_PATH=/mnt/scopearray/mm/ImageJ/lib/micro-manager ipython -c '
import MMCorePy as mm
core = mm.CMMCore()
core.loadSystemConfiguration("/mnt/scopearray/mm/ImageJ/MMConfig1.cfg")
core.setConfig("acquisition mode", "5X brightfield")

%gui qt
from PyQt5 import QtCore, QtGui, QtWidgets, QtOpenGL
from ris_widget_standin import RisWidgetStandin
import ctypes as ct
import numpy as np

rw = RisWidgetStandin()
rw.show()
' -i
