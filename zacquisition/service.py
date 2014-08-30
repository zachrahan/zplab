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

import enum
import gevent
import pathlib
import socket
import threading
import weakref
import zmq.green as zmq
from zacquisition.service_property import ServiceProperty
from zacquisition import service_property_validators as spvs

class _ClientEventThread(threading.Thread):
    _nextId = 0
    _nextIdLock = threading.Lock()

    def __init__(self, service, eventSocketURI):
        super().__init__()
        self._service = weakref.ref(service)
        self._eventSocketURI = eventSocketURI
        with self._nextIdLock:
            id_ = _ClientEventThread._nextId
            _ClientEventThread._nextId += 1
        self._stopThreadSocketURI = 'inproc://_ClientEventThread__{}'.format(id_)
        self._stopThreadSendSocket = self._service()._zc.socket(zmq.PAIR)
        self._stopThreadSendSocket.bind(self._stopThreadSocketURI)

    def _stopThreadSocketListener(self):
        '''"_stopThreadSocketListener" in the sense "listen to a stop socket" and not "stop a socket listener".'''
        while True:
            s = self._stopThreadReceiveSocket.recv_string()
            if s == 'stop':
                self._eventSocketListenerGt.kill()
                break

    def _eventSocketListener(self):
        while True:
            md = self._eventSocket.recv_json()

    def run(self):
        self._eventSocket = self._service()._zc.socket(zmq.SUB)
        self._eventSocket.connect(self._eventSocketURI)
        self._stopThreadReceiveSocket = self._service()._zc.socket(zmq.PAIR)
        self._stopThreadReceiveSocket.connect(self._stopThreadSocketURI)
        self._eventSocketListenerGt = gevent.spawn(self._eventSocketListener)
        self._stopThreadSocketListenerGt = gevent.spawn(self._stopThreadSocketListener)
        gevent.wait((self._eventSocketListenerGt, self._stopThreadSocketListenerGt))

    def stop(self):
        self._stopThreadSendSocket.send_string('stop')

class Service:
    class InstanceType(enum.Enum):
        Daemon = 1
        Client = 2

    daemonHostName = ServiceProperty(default=None, name='daemonHostName', validators=spvs.readOnly)
    ipcSocketPath = ServiceProperty(default=None, name='ipcSocketPath', validators=spvs.readOnly)
    eventIpcSocketFPath = ServiceProperty(default=None, name='eventIpcSocketFPath', validators=spvs.readOnly)
    commandIpcSocketFPath = ServiceProperty(default=None, name='commandIpcSocketFPath', validators=spvs.readOnly)
    eventTcpPortNumber = ServiceProperty(default=None, name='eventTcpPortNumber', validators=spvs.readOnly)
    commandTcpPortNumber = ServiceProperty(default=None, name='commandTcpPortNumber', validators=spvs.readOnly)
    pyClassString = ServiceProperty(default=None, name='pyClassString', validators=spvs.readOnly)
    # Because service name is used to identify the Unix domain socket (IPC socket), service name can only be set by providing
    # a name argument to __init__(..) and is otherwise read-only.
    name = ServiceProperty(default='UNNAMED SERVICE', name='name', validators=spvs.readOnly)

    def __init__(self, pyClassString, zmqContext=None, instanceType=InstanceType.Daemon, parent=None, name=None, \
                 ipcSocketPath='/tmp/zacquisition', eventTcpPortNumber=51500, commandTcpPortNumber=51501, \
                 daemonHostName=None):
        '''ipcPathPrefix, eventTcpPortNumber, and commandTcpPortNumber are only used if parent is None.
        If parent is not None, these values are computed from those of the parent and the values supplied
        are ignored.

        If instanceType is Client and daemonHostName is None, the daemon is assumed to be accessible via IPC.
        If instanceType is Daemon, specifying daemonHostName overrides the default behavior of using
        socket.gethostname(), which is useful in the case where clients will connect to the daemon over the
        network without being able to resolve the daemon host name to an IP, requiring daemon host name to
        be specified directly as an IP address.'''

        # Enumerate ServiceProperties so that a list of their names is available via the serviceProperties property
        # (which is itself a standard Python property and not a ServiceProperty descriptor instance).
        self._serviceProperties = set()
        for type_ in self.__class__.mro()[:-1]:
            for attrName, attrInstance in type_.__dict__.items():
                if issubclass(type(attrInstance), ServiceProperty):
                    self._serviceProperties.add(attrName)

        if type(pyClassString) is not str:
            raise TypeError('pyClassString must be of type str.')
        Service.pyClassString.setWithoutValidating(self, pyClassString)

        if zmqContext is None:
            self._zc = zmq.Context()
        else:
            self._zc = zmqContext

        if name is not None:
            name = str(name)
            Service.name.setWithoutValidating(self, name)

        if parent is None:
            self._parent = None
        else:
            if not issubclass(type(parent), Service):
                raise TypeError('parent must be a sub class of zacquisition.Service.')
            self._parent = parent

        self._children = []

        # Note that the typecast causes a ValueError to be raised if nonsense is supplied for instanceType
        self._instanceType = Service.InstanceType(instanceType)

        if self._instanceType == Service.InstanceType.Daemon:
            self._daemonInit(ipcSocketPath, eventTcpPortNumber, commandTcpPortNumber, daemonHostName)
        else:
            self._clientInit(ipcSocketPath, eventTcpPortNumber, commandTcpPortNumber, daemonHostName)

    def _daemonInit(self, ipcSocketPath, eventTcpPortNumber, commandTcpPortNumber, daemonHostName):
        if daemonHostName is None:
            daemonHostName = socket.gethostname()
        Service.daemonHostName.setWithoutValidating(self, daemonHostName)
        self._eventSocket = self._zc.socket(zmq.PUB)
        self._commandSocket = self._zc.socket(zmq.REP)
        if self._parent is None:
            ipcsp = pathlib.Path(ipcSocketPath)
            etcpn = eventTcpPortNumber
            rtcpn = commandTcpPortNumber
        else:
            # Use directory in which parent's IPC sockets reside as IPC path prefix
            ipcsp = self._parent.ipcSocketPath
            etcpn = self._parent.eventTcpPortNumber + 2
            rtcpn = self._parent.commandTcpPortNumber + 2
        # Place our IPC socket in a subdirectory with our (this service's) name
        ipcsp /= self.name
        if not ipcsp.exists():
            ipcsp.mkdir(parents=True)
        eipcsfp = ipcsp / (self.name + '__EVENT__.ipc')
        ripcsfp = ipcsp / (self.name + '__REQUEST__.ipc')
        Service.ipcSocketPath.setWithoutValidating(self, ipcsp)
        # Use our name for IPC socket filenames
        self._eventSocket.bind('ipc://' + str(eipcsfp))
        self._commandSocket.bind('ipc://' + str(ripcsfp))
        Service.eventIpcSocketFPath.setWithoutValidating(self, eipcsfp)
        Service.commandIpcSocketFPath.setWithoutValidating(self, ripcsfp)
        if self._parent is None:
            # If we are using port numbers supplied directly by the user, then only those ports will do
            self._eventSocket.bind('tcp://*:{}'.format(etcpn))
            self._commandSocket.bind('tcp://*:{}'.format(rtcpn))
        else:
            # If we are using computed port numbers, then we use the first available ports greater than or
            # equal to desired
            def openTcpPort(port, number):
                while True:
                    try:
                        port.bind('tcp://*:{}'.format(number))
                        break
                    except zmq.ZMQError:
                        number += 1
                        if number >= 65536:
                            raise RuntimeError('Failed to find available TCP port number.')
                return number
            etcpn = openTcpPort(self._eventSocket, etcpn)
            rtcpn = openTcpPort(self._commandSocket, rtcpn)
        Service.eventTcpPortNumber.setWithoutValidating(self, etcpn)
        Service.commandTcpPortNumber.setWithoutValidating(self, rtcpn)

        self._daemonCommandSocketListenerGt = gevent.spawn(self._daemonCommandSocketListener)

    def _clientInit(self, ipcSocketPath, eventTcpPortNumber, commandTcpPortNumber, daemonHostName):
        self._commandSocket = self._zc.socket(zmq.REQ)
        self._clientEventThread = _ClientEventThread(self, self._eventSocketURI)

    def describeRecursive(self):
        ret = \
        {
            'daemonHostName':self.daemonHostName,
            'pyClassString':self.pyClassString,
            'name':self.name,
            'eventIpcSocketFPath':str(self.eventIpcSocketFPath),
            'commandIpcSocketFPath':str(self.commandIpcSocketFPath),
            'eventTcpPortNumber':self.eventTcpPortNumber,
            'commandTcpPortNumber':self.commandTcpPortNumber,
            'children':[child[1].describeRecursive() for child in self.children]
        }
        return ret

    def _daemonCommandSocketListener(self):
        while True:
            md = self._commandSocket.recv_json()
            assert(issubclass(type(md), dict))
            if md['type'] == 'query':
                replyMd = {'type':'query reply',
                           'query':md['query']}
                self._commandSocket.send_json(replyMd, zmq.SNDMORE)
                if md['query'] == 'describe recursive':
                    replyMd = self.describeRecursive()
                    replyMd['disposition'] = 'ok'
                    self._commandSocket.send_json(replyMd)
            elif md['type'] == 'command':
                replyMd = {'type':'command reply',
                           'command':md['command']}
                self._commandSocket.send_json(replyMd, zmq.SNDMORE)
                if md['command'] == 'shut down':
                    self._commandSocket.send_json({'disposition':'ok'})

    def _sendChangePropCommand(self, name, value):
        pass

    def _sendPropChangedNotification(self, name, value):
        pass

    @property
    def serviceProperties(self):
        '''Returns a list of the names of ServiceProperties provided by this instance.  At minimum, this list
        contains ['name'].'''
        return self._serviceProperties

    @property
    def instanceType(self):
        '''instanceType is represented as a plain Python property and not a ServiceProperty because a Service daemon's
        instanceType is always Service.InstanceType.Daemon, whereas the instanceType of clients is always
        Service.InstanceType.Client.  ServiceProperties are synchronized between daemon and client and indicate something
        about the device being represented, whereas instanceType is a property of the interface object or backend object
        itself.'''
        return self._instanceType

    @property
    def parent(self):
        return self._parent

    @property
    def children(self):
        return self._children

#def makeClientTree(zmqContext, uri):
#    req_socket = zmqContext.socket(zmq.REQ)
#    req_socket.connect(uri)
#    req_socket.send_json({'type':'query',
#                          'query':'describe recursive'})
#    rep = req_socket.recv_json()
#    if rep['type'] != 'query reply':
#        raise RuntimeError('Reply received for "describe recursive" query is not a "query reply", but a "{}".'.format(rep['type']))

