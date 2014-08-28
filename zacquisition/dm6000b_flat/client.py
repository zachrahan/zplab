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

import zmq

class Dm6000b_Client:
    def __init__(self, zmqContext, daemonControlUri):
        self._zc = zmqContext
        self._daemonControlUri = daemonControlUri
        self._reqSocket = self._zc.socket(zmq.REQ)
        self._reqSocket.connect(self._daemonControlUri)

    def waitForReady(self):
        self._reqSocket.send_json({'command':'ping'})
        md = self._reqSocket.recv_json()
        if md.get('reply to command') != 'ping' or md.get('reply') != 'pong':
            raise RuntimeError('Received incorrect reply to "ping" command.')

    def shutDownDaemon(self):
        self._reqSocket.send_json({'command':'shut down'})
        md = self._reqSocket.recv_json()
        if md.get('reply to command') != 'shut down' or md.get('reply') != 'shutting down':
            raise RuntimeError('Received incorrect reply to "shut down" command.')

    def blockDaemonFor(self, seconds):
        self._reqSocket.send_json({'command':'block',
                                   'seconds':seconds})
        md = self._reqSocket.recv_json()
        if md.get('reply to command') != 'block' or md.get('reply') not in ('blocking...', 'block complete'):
            raise RuntimeError('Received incorrect reply to "block" command.')

    @property
    def async(self):
        self._reqSocket.send_json({'command':'get async'})
        md = self._reqSocket.recv_json()
        if md.get('reply to command') != 'get async' or 'async' not in md:
            raise RuntimeError('Received incorrect reply to "get async" command.')
        return md['async']

    @async.setter
    def async(self, async):
        self._reqSocket.send_json({'command':'set async',
                                   'async':async})
        md = self._reqSocket.recv_json()
        if md.get('reply to command') != 'set async' or md.get('reply') != 'async set':
            raise RuntimeError('Received incorrect reply to "set async" command.')
