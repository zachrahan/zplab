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
import zmq.green as zmq
from zacquisition.service_property import ServiceProperty
from zacquisition import service_property_validators as spvs

class Service:
    class InstanceType(enum.Enum):
        Daemon = 1
        Client = 2

    ipcSocketPath = ServiceProperty(default=None, validators=spvs.readOnly)
    eventIpcSocketFPath = ServiceProperty(default=None, validators=spvs.readOnly)
    reqIpcSocketFPath = ServiceProperty(default=None, validators=spvs.readOnly)
    eventTcpPortNumber = ServiceProperty(default=None, validators=spvs.readOnly)
    reqTcpPortNumber = ServiceProperty(default=None, validators=spvs.readOnly)
    pyClassString = ServiceProperty(default=None, validators=spvs.readOnly)
    # Because service name is used to identify the Unix domain socket (IPC socket), service name can only be set by providing
    # a name argument to __init__(..) and is otherwise read-only.
    name = ServiceProperty(default='UNNAMED SERVICE', validators=spvs.readOnly)

    def __init__(self, pyClassString, zmqContext=None, instanceType=InstanceType.Daemon, parent=None, name=None, \
                 ipcSocketPath='/tmp/zacquisition', eventTcpPortNumber=51500, reqTcpPortNumber=51501):
        '''ipcPathPrefix, eventTcpPortNumber, and reqTcpPortNumber are only used if parent is None.  If parent is not None,
        these values are computed from those of the parent and the values supplied are ignored.'''
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
            self._pubSocket = self._zc.socket(zmq.PUB)
            self._repSocket = self._zc.socket(zmq.REP)
            if self._parent is None:
                ipcsp = pathlib.Path(ipcSocketPath)
                etcpn = eventTcpPortNumber
                rtcpn = reqTcpPortNumber
            else:
                # Use directory in which parent's IPC sockets reside as IPC path prefix
                ipcsp = self._parent.ipcSocketPath
                etcpn = self._parent.eventTcpPortNumber + 2
                rtcpn = self._parent.reqTcpPortNumber + 2
            # Place our IPC socket in a subdirectory with our (this service's) name
            ipcsp /= self.name
            if not ipcsp.exists():
                ipcsp.mkdir(parents=True)
            eipcsfp = ipcsp / (self.name + '__EVENT__.ipc')
            ripcsfp = ipcsp / (self.name + '__REQUEST__.ipc')
            Service.ipcSocketPath.setWithoutValidating(self, ipcsp)
            # Use our name for IPC socket filenames
            self._pubSocket.bind('ipc://' + str(eipcsfp))
            self._repSocket.bind('ipc://' + str(ripcsfp))
            Service.eventIpcSocketFPath.setWithoutValidating(self, eipcsfp)
            Service.reqIpcSocketFPath.setWithoutValidating(self, ripcsfp)
            if self._parent is None:
                # If we are using port numbers supplied directly by the user, then only those ports will do
                self._pubSocket.bind('tcp://*:{}'.format(etcpn))
                self._repSocket.bind('tcp://*:{}'.format(rtcpn))
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
                etcpn = openTcpPort(self._pubSocket, etcpn)
                rtcpn = openTcpPort(self._repSocket, rtcpn)
            Service.eventTcpPortNumber.setWithoutValidating(self, etcpn)
            Service.reqTcpPortNumber.setWithoutValidating(self, rtcpn)

            self._reqListenerGreenlet = gevent.spawn(self._reqListener)

    def _describeRecursive(self):
        ret = {'pyClassString':self.pyClassString,
               'name':self.name,
               'ipcSocketPath':str(self.ipcSocketPath)

    def _reqListener(self):
        '''Intended to run in a greenlet.'''
        while True:
            md = self._repSocket.recv_json()
            if issubclass(type(md), dict):
                if md['type'] == 'query':
                    if md['query'] == 'describe recursive':


    @property
    def serviceProperties(self):
        '''Returns a list of the names of ServiceProperties provided by this instance.  At minimum, this list
        contains ['name'].'''
        return self._serviceProperties.copy()

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

def makeClientTree(zmqContext, uri):
    req_socket = zmqContext.socket(zmq.REQ)
    req_socket.connect(uri)
    req_socket.send_json({'type':'query',
                          'query':'describe recursive'})
    rep = req_socket.recv_json()
    if rep['type'] != 'query reply':
        raise RuntimeError('Reply received for "describe recursive" query is not a "query reply", but a "{}".'.format(rep['type']))

