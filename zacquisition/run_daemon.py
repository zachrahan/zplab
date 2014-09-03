#!/usr/bin/env python3

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

import gevent
import pathlib
import re
import signal
import sys
import time

zplSourceDir = str(pathlib.Path(__file__).absolute().parent.parent)

args = sys.argv.copy()
args.reverse()
args.pop()
classPackageAndName = args.pop()
match = re.match(r'^(.+)\.([^.]+)$', classPackageAndName)
assert(match)
classPackage = match.group(1)
className = match.group(2)
args.insert(0, 'instanceType=zacquisition.service.Service.InstanceType.Daemon')
execLines = ['sys.path.insert(0, "{}")'.format(zplSourceDir)]
execLines.append('import zacquisition.service')
execLines.append('import ' + classPackage)
execLines.append('''prevShutdownPrintTime = None
def keyboardInterruptHandler():
    global prevShutdownPrintTime
    global daemon
    curTime = time.time()
    if prevShutdownPrintTime is None or curTime - prevShutdownPrintTime > 0.5:
        print('shutting down "{}"...'.format(classPackageAndName))
        prevShutdownPrintTime = curTime
    daemon.daemonGreenThreads.kill()''')
execLines.append('gevent.signal(signal.SIGINT, keyboardInterruptHandler)')
execLines.append('daemon = {}({})'.format(classPackageAndName, ', '.join(args)))
execLines.append('gevent.signal(signal.SIGINT, keyboardInterruptHandler)')
execLines.append('daemon.daemonGreenThreads.join()')

execStr = '\n'.join(execLines)
exec(execStr)
