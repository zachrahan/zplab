#!/usr/bin/env python3
# Copyright 2014 WUSTL ZPLAB

from pathlib import Path
import subprocess
import sys

class _Binary:
    def __init__(self, fileType = None, isTarget = False):
        self.fileType = fileType
        self.isTarget = isTarget

class _FixDylibInternalPaths:
    def __init__(self, targetFNs, dylibDirs, verbose, recursive):
        self.targetFNs = targetFNs
        self.dylibDirs = dylibDirs
        self.verbose = verbose
        self.recursive = recursive

    def _getFileType(self, p):
        t = subprocess.check_output(['file', '-b', str(p)]).decode(encoding = 'UTF-8').rstrip()
        if t == 'Mach-O 64-bit executable x86_64':
            return 'executable'
        elif t == 'Mach-O 64-bit dynamically linked shared library x86_64':
            return 'dylib'

    def _gatherTargets(self):
        self.targets = dict()
        for targetFN in self.targetFNs:
            p = Path(targetFN)
            if not p.exists():
                print('Failed to find binary "{}", skipping.'.format(binary), file = sys.stderr)
            elif not p.is_file():
                print('"{}" is not a regular file or a symlink that points to a regular file; skipping.'.format(binary), file = sys.stderr)
            else:
                fileType = self._getFileType(p)
                if fileType != 'executable' and fileType != 'dylib':
                    print('"{}" is neither an executable nor a dylib; skipping.'.format(binary), file = sys.stderr)
                else:
                    absPath = p.resolve()
                    if absPath not in self.targets:
                        self.targets[absPath] = _Binary(fileType, True)

    def _gatherDylibs(self):
        pass

    def _compute():

    def execute(self):
        self._gatherBinaries()
        

def fixDylibInternalPaths(dylibFNs, depDirs, verbose = False):
    '''OSX can store relative or absolute paths of dylib dependencies in addition to the relative or absolute
    path of the dylib itself.  When a binary linking against a dylib is built, the field describing the dylib's
    location is copied to the corresponding dependency field in the binary.  Thus, if a dylib contains its own
    location as an absolute path, any binary linked against it in the future will be able to find it.

    This function updates this stored information so dylibs required by other dylibs and dylibs required by
    executables that are stored in custom locations can be found without resorting to DYLD_LIBRARY_PATH environment
    variable.

    Dylibs (executables and/or dylibs) specified by the dylibFNs argument are updated to store their own IDs
    as absolute paths so that any binaries linked against them in the future will remember where they are.  Additionally,
    any executables or binaries found in depDirs are updated so that any references to any of the dylibs specified by
    dylibFNs '''

    fixer = _FixDylibInternalPaths(targetFNs, dylibDirs, verbose)
    fixer.execute()
    del fixer

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('-v', '--verbose', action = 'store_true', help = 'output progress information during execution')
    parser.add_argument('-b', '--targets', metavar = 'target', nargs = '+', help = 'binaries (executables and dylibs) to update', required = True)
    parser.add_argument('-d', '--dylib-paths', metavar = 'dylib_path', nargs = '+', help = 'directories to search for dependancies', required = True)
    parser.add_argument('-r', '--recursive', action = 'store_true', help = 'search dylib directories recursively; note that symbolic links are ignored')
    args = parser.parse_args()

    fixDylibInternalPaths(args.targets, args.dylib_paths, args.verbose, args.recursive)
