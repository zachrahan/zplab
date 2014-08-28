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
import threading
import zmq.green as zmq
from zacquisition.service import Service
from zacquisition.service_property import ServiceProperty
from zacquisition import service_property_validators as spvs

from zacquisition.camera.andor import Camera

class Root(Service):
    def __init__(self, zmqContext=None, instanceType=Service.InstanceType.Daemon, parent=None, name='Service Tree Root', \
                 ipcSocketPath='/tmp/zacquisition', eventTcpPortNumber=51500, reqTcpPortNumber=51501):
        super().__init__('zacquisition.root.root', zmqContext, instanceType, parent, name, \
                         ipcSocketPath, eventTcpPortNumber, reqTcpPortNumber)

        if instanceType == Service.InstanceType.Daemon:
            self._makeServiceTree()

    def _makeServiceTree(self):
        self._camera = Camera(self._zc, parent=self)
        self._children.append(('camera', self._camera))

    @property
    def camera(self):
        return self._camera

def makeRootDaemonTree(zmqContext=None, name='Service Tree Root', ipcSocketPath='/tmp/zacquisition', eventTcpPortNumber=51500, reqTcpPortNumber=51501):
    '''Suppose you want to use the Root backend in an iPython interactive session.  You may instantiate Root directly,
    but because you are retaining control of the main thread, none of Root's greenlets will have an opportunity to
    execute unless you do gevent.wait() or equivalent.  However, gevent.wait() will block forever, preventing you
    from interacting further.  Furthermore, strange and bad things will happen if you attempt to gevent.wait() from
    another thread in order to sidestep the block.  These strange and bad things occur for two reasons:
    1) A wait on a greenlet belonging to another thread never completes.
    2) Zeromq sockets must not be used from a thread other than the thread that created the socket.

    The solution is to have the background thread doing the gevent.wait() own everything.  This requires that
    everything be created in the background thread, which is what we do here.  Thus, the main thread remains responsive
    to the user without breaking all of our gevent and zeromq stuff.'''
    root = None
    rootLock = threading.Lock()
    rootSetEvent = threading.Event()
    def threadProc():
        nonlocal root
        loop = gevent.get_hub().loop
        with rootLock:
            root = Root(zmqContext, name=name, ipcSocketPath=ipcSocketPath, eventTcpPortNumber=eventTcpPortNumber, reqTcpPortNumber=reqTcpPortNumber)
        rootSetEvent.set()
        while True:
            loop.run()
    thread = threading.Thread(target=threadProc)
    thread.start()
    rootSetEvent.wait()
    with rootLock:
        return root, thread
