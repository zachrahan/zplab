#!/usr/bin/env bash

args=("$@")
unamestr=`uname`

if [[ "$unamestr" == 'Darwin' ]]; then
    python3.4 /Applications/SlickEdit2013.app/Contents/resource/tools/pydbgp-1.1.0-1/bin/py3_dbgp.py -d 127.0.0.1:${args[0]} -k slickedit ${args[@]:1}
else
    python ~ehvatum/slickedit/resource/tools/pydbgp-1.1.0-1/bin/py3_dbgp.py -d 127.0.0.1:${args[0]} -k slickedit ${args[@]:1}
fi
