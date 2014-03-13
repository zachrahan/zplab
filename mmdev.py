#!/usr/bin/env python3

import MMCorePy

core = MMCorePy.CMMCore()
core.loadSystemConfiguration("/mnt/scopearray/mm/ImageJ/MMConfig1.cfg")
print(core.getLoadedDevices())
