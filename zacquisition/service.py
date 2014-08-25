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
import zmq
from zacquisition.service_property import ServiceProperty
from zacquisition import service_property_validators as spvs

class Service:
    # Because service name is used to identify the Unix domain socket (IPC socket), service name can only be set by providing
    # a name argument to __init__(..) and is otherwise read-only.
    name = ServiceProperty(default='UNNAMED SERVICE', validators=spvs.readOnly)

    def __init__(self, zmqContext=None, name=None):
        # Enumerate ServiceProperties so that a list of their names is available via the serviceProperties property
        # (which is itself a standard Python property and not a ServiceProperty descriptor instance).
        self._serviceProperties = set()
        for type_ in self.__class__.mro()[:-1]:
            for attrName, attrInstance in type_.__dict__.items():
                if issubclass(type(attrInstance), ServiceProperty):
                    self._serviceProperties.add(attrName)

        if zmqContext is None:
            self._zc = zmq.Context()
        else:
            self._zc = zmqContext

        if name is not None:
            name = str(name)
            Service.name.setWithoutValidating(self, name)

    @property
    def serviceProperties(self):
        '''Returns a list of the names of ServiceProperties provided by this instance.  At minimum, this list
        contains ['name'].'''
        return self._serviceProperties.copy()
