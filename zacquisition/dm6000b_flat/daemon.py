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

import collections
import serial
import threading
import time
import zmq

class _FutureResponse:
    def __init__(self, responseCallback=None):
        self.hasResponse = threading.Event()
        self.responseDispositionCode = None
        self.responseParameters = None
        self.responseCallback = responseCallback

    def get_response(self):
        self.hasResponse.wait()
        return (self.responseDispositionCode, self.responseParameters)

    def _set_response(self, responseDispositionCode, responseParamters):
        self.responseDispositionCode = responseDispositionCode
        self.responseParameters = responseParamters
        self.hasResponse.set()
        if self.responseCallback:
            responseCallback(self.responseDispositionCode, self.responseParameters)

class _Router(threading.Thread):
    def __init__(self, serialPortDescriptor):
        super().__init__()
        self._serialPort = serial.Serial(serialPortDescriptor, baudrate=115200)
        self._receiveRegistry = collections.defaultdict(list)

    def run(self):
        while True:
            line = self._readLine()
            if line[0] != '$' and len(line) >= 5:
                self._receive(line[0:2], line[2:3], line[3:5], line[5:])

    def sendMessage(self, message, responseCallback=None):
        assert(len(message) >= 5)
        assert(message[2] == '0')
        response = _FutureResponse(responseCallback)
        self._send(message, response)
        return response

    def _send(self, message, response):
        responseId = message[0:2] + message[3:5]
        message = message.encode('utf-8')
        self._receiveRegistry[responseId].append(response)

    def _receive(self, functionUnitId, dispositionCode, commandId, parameters):
        responseId = functionUnitId + commandId # NB: this represents string concatenation
        if responseId in self._receiveRegistry:
            responses = self._receiveRegistry.pop(responseId)
            for response in responses:
                response._set_response(dispositionCode, parameters)

    def _readLine(self):
        line = ''
        while True:
            c = self._serialPort.read().decode('utf-8')
            if c == '\r':
                break
            else:
                line += c

class Dm6000b_Daemon:
    def __init__(self, zmqContext, controlUri, serialPort='/dev/ttyScope'):
        self._zc = zmqContext
        self._controlUri = controlUri
        self._repSocket = self._zc.socket(zmq.REP)
        self._repSocket.bind(self._controlUri)
        self._async = False
        self._router = _Router(serialPort)
        self._router.start()

    def run(self):
        while self._takeReq:
            pass

    def _handlePing(self, replyMd):
        self._repSocket.send_json({'reply to command':'ping',
                                   'reply':'pong'})
        return True

    def _handleShutDown(self, replyMd):
        print('shutting down...')
        self._repSocket.send_json({'reply to command':'shut down',
                                   'reply':'shutting down'})
        return False

    def _handleBlock(self, replyMd, seconds):
        md = {'reply to command':'block'}
        if self._async:
            md['reply'] = 'blocking...'
            self._repSocket.send_json(md)
            time.sleep(seconds)
        else:
            time.sleep(seconds)
            md['reply'] = 'block complete'
            self._repSocket.send_json(md)
        return True

    def _handleGetAsync(self, replyMd):
        self._repSocket.send_json({'reply to command':'get async',
                                   'async':self._async})
        return True

    def _handleSetAsync(self, replyMd, async):
        self._async = async
        self._repSocket.send_json({'reply to command':'set async',
                                   'reply':'async set'})
        return True

    def _defaultHandler(self, replyMd):
        print('received unknown command')
        self._repSocket.send_json({'error':'unknown command'})
        return True

    handlers = \
    {
        'ping' : _handlePing,
        'shut down' : _handleShutDown,
        'block' : _handleBlock,
        'get async' : _handleGetAsync,
        'set async' : _handleSetAsync
    }

    def _takeReq(self):
        print('_takeReq')
        md = self._repSocket.recv_json()
        print(md)
        command = md.get('command')
        if 'command' in md:
            del md['command']
        return Dm6000b_Daemon.handlers.get(command, Dm6000b_Daemon._defaultHandler)(self, **md)

if __name__ == '__main__':
    import sys
    context = zmq.Context()
    dm6000b_daemon = Dm6000b_Daemon(context, sys.argv[1])
    dm6000b_daemon.run()
