#!/usr/bin/env bash

args=("$@")
python ~ehvatum/slickedit/resource/tools/pydbgp-1.1.0-1/bin/py3_dbgp.py -d 127.0.0.1:${args[0]} -k slickedit ${args[@]:1}
