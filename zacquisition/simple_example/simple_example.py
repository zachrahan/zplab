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
import gevent.pool
import subprocess
import threading
import zmq.green as zmq
from zacquisition.service import Service
from zacquisition.service_property import ServiceProperty
from zacquisition import service_property_validators as spvs

class SimpleExampleService(Service):
    def __init__(self, zmqContext=None, instanceType=Service.InstanceType.Client, parent=None, name="Simple Example Service",
                 ipcSocketPath='/tmp/zacquisition', eventTcpPortNumber=51500, commandTcpPortNumber=51501,
                 daemonHostName=None):
        super().__init__('zacquisition.simple_example.simple_example.SimpleExampleService',
                         zmqContext, instanceType, parent, name,
                         ipcSocketPath, eventTcpPortNumber, commandTcpPortNumber,
                         daemonHostName)
        if self.instanceType == Service.InstanceType.Daemon:
            self._childDaemons = []
            self._childDaemons.append(subprocess.Popen(['/home/ehvatum/zplrepo/zacquisition/run_daemon.py zacquisition.simple_example.simple_example.SimpleExampleChildService'], shell=True))
            self._exampleChild = SimpleExampleChildService(self._zc, parent=self, daemonHostName=self.daemonHostName, ipcSocketPath=self.ipcSocketPath)
            self._children.append(('childservice', self._exampleChild))

class SimpleExampleChildService(Service):
    def __init__(self, zmqContext=None, instanceType=Service.InstanceType.Client, parent=None, name="Simple Example Child Service",
                 ipcSocketPath='/tmp/zacquisition', eventTcpPortNumber=51502, commandTcpPortNumber=51503,
                 daemonHostName=None):
        super().__init__('zacquisition.simple_example.simple_example.SimpleExampleChildService',
                         zmqContext, instanceType, parent, name,
                         ipcSocketPath, eventTcpPortNumber, commandTcpPortNumber,
                         daemonHostName)


#class SimpleExampleService:
#    def __init__(self, blarf):
#        self._zc = zmq.Context()
#        self.daemonGreenThreads = gevent.pool.Group()
#        self._commandSocket = self._zc.socket(zmq.REP)
#        self._commandSocket.bind('tcp://*:55555')
#        self._fooSocket = self._zc.socket(zmq.REP)
#        self._fooSocket.bind('tcp://*:55556')
#        self._commandSocketListenerGt = gevent.spawn(self._commandSocketListener)
#        self._fooSocketListenerGt = gevent.spawn(self._fooSocketListener)
#        self.daemonGreenThreads.add(self._commandSocketListenerGt)
#        self.daemonGreenThreads.add(self._fooSocketListenerGt)
#
#    def _commandSocketListener(self):
#        while True:
#            s = self._commandSocket.recv_string()
#            self._commandSocket.send_string('ok')
#            if s == 'shut down':
#                print('shutting down...')
#                self._fooSocketListenerGt.kill()
#                break
#
#    def _fooSocketListener(self):
#        while True:
#            s = self._fooSocket.recv_string()
#            print(s)
#            self._fooSocket.send_string('foo')
