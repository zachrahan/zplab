#!/usr/bin/env python3.4
# This script simply serves as a debugging target for Python debuggers that are able to launch a script but not
# a module in the python -m fashion.

from rpc_acquisition.scope import scope_server
scope_server.simple_server_main('*', verbose=True)
