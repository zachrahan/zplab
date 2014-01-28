#!/usr/bin/env python3
# Copyright 2014 WUSTL ZPLAB

from pathlib import Path

class _FixDylibInternalPaths:
    def __init__(self, limitToPaths, limitToFiles, verbose):
        if limitToPaths is None and limitToFiles is None:
            raise ValueError('fixDylibInternalPaths(limitToPaths = None, limitToFiles = None, verbose = False): both limitToPaths and limitToFiles are None.')

            if limitToPaths is not None and limitToFiles is not None:
                raise ValueError('fixDylibInternalPaths(limitToPaths = None, limitToFiles = None, verbose = False): both limitToPaths were limitToFiles specified.')

    def execute(self):
        pass

def fixDylibInternalPaths(limitToPaths = None, limitToFiles = None, verbose = False):
    '''OSX can store relative or absolute paths of dylib dependencies in addition to the relative or absolute
    path of the dylib itself which is copied to the dependancy info of any binary linked against it.

    This function updates this stored information so that other dylibs required by a dylib can be found without
    resorting to the DYLD_LIBRARY_PATH environment variable.  Additionally, any binaries linked against the updated
    dylib retain the path to the dylib.

    If only limitToPaths is specified, all dylibs in the paths specified will be processed.
    If only limitToFiles is specified, only the dylibs specified by filename will be processed.
    If neither or both are specified, an exception is thrown.'''

    fixer = _FixDylibInternalPaths(limitToPaths, limitToFiles, verbose)
    fixer.execute()
    del fixer

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required = True)
    group.add_argument('--by-file', action = 'store_true')
    group.add_argument('--by-directory', action = 'store_true')
    parser.add_argument('targets', help='dylib files or dylib directories to process')
    args = parser.parse_args()
