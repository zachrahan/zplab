#!/usr/bin/env bash

PYTHONPATH=/mnt/scopearray/mm/micro-manager/MMCorePy_wrap/build/lib.linux-x86_64-3.3 LD_LIBRARY_PATH=/mnt/scopearray/mm/ImageJ/lib/micro-manager ipython -c 'import MMCorePy as mm
core = mm.CMMCore()
core.loadSystemConfiguration("/mnt/scopearray/mm/ImageJ/MMConfig1.cfg")' -i
