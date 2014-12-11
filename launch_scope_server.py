#!/usr/bin/env python3.4
# This script simply serves as a debugging target for Python debuggers that are able to launch a script but not
# a module in the python -m fashion.

from rpc_acquisition import scope_server
scope_server.server_main(verbose=True)
