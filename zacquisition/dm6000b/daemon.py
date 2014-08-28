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

import time
import zmq

class Dm6000b_Daemon:
    def __init__(self, zmqContext, controlUri):
        self._zc = zmqContext
        self._controlUri = controlUri
        self._repSocket = self._zc.socket(zmq.REP)
        self._repSocket.bind(self._controlUri)
        print(controlUri)
        self._async = False
        while self._takeReq():
            pass

    def _handlePing(self):
        self._repSocket.send_json({'reply_to_command':'ping',
                                   'reply':'pong'})
        return True

    def _handleShutDown(self):
        print('shutting down...')
        self._repSocket.send_json({'reply_to_command':'shut down',
                                   'reply':'shutting down'})
        return False

    def _handleBlock(self, seconds):
        md = {'reply_to_command':'block'}
        if self._async:
            md['reply'] = 'blocking...'
            self._repSocket.send_json(md)
            time.sleep(seconds)
        else:
            time.sleep(seconds)
            md['reply'] = 'block complete'
            self._repSocket.send_json(md)
        return True

    def _handleGetAsync(self):
        self._repSocket.send_json({'reply_to_command':'get async',
                                   'async':self._async})
        return True

    def _handleSetAsync(self, async):
        self._async = async
        self._repSocket.send_json({'reply_to_command':'set async',
                                   'reply':'async set'})
        return True

    def _defaultHandler(self):
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
