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
# Authors: Zach Pincus

import zmq

from .simple_rpc import rpc_server, property_server
from . import scope
from .util import transfer_ism_buffer
from .util import logging
from .config import scope_configuration

class ScopeServer:
    def __init__(self, host):
        rpc_addr = scope_configuration.rpc_addr(host)
        interrupt_addr = scope_configuration.interrupt_addr(host)
        property_addr = scope_configuration.property_addr(host)
        context = zmq.Context()

        property_update_server = property_server.ZMQServer(property_addr, context=context)

        scope_controller = scope.Scope(property_update_server)
        # add transfer_ism_buffer as hidden elements of the namespace, which RPC clients can use for seamless buffer sharing
        scope_controller._transfer_ism_buffer = transfer_ism_buffer

        interrupter = rpc_server.ZMQInterrupter(interrupt_addr, context=context)
        self.scope_server = rpc_server.ZMQServer(scope_controller, interrupter, rpc_addr, context=context)

    def run(self):
        self.scope_server.run()

def simple_server_main(host, verbose=False):
    logging.set_verbose(verbose)
    server = ScopeServer(host)
    print('Scope Server Ready (Listening on {})'.format(host))
    try:
        server.run()
    except KeyboardInterrupt:
        return

if __name__ == '__main__':
    import argparse
    config = scope_configuration.get_config()
    parser = argparse.ArgumentParser(description="Run the microscope server")
    parser.add_argument("--public", action='store_true', help="Allow network connections to the server [default: allow only local connections]")
    parser.add_argument("--verbose", action='store_true', help="Print human-readable representations of all RPC calls and property state changes to stdout.")
    args = parser.parse_args()
    host = config.Server.PUBLICHOST if args.public else config.Server.LOCALHOST
    simple_server_main(host, verbose=args.verbose)
