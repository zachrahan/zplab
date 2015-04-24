#!/usr/bin/env python3

# The MIT License (MIT)
#
# Copyright (c) 2014-2015 WUSTL ZPLAB
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

from pathlib import Path
import sys

INCLUDED_FILE_EXTENSIONS = {
    '.py',
    '.pyx',
    '.pxi',
    '.c',
    '.cpp',
    '.cxx',
    '.h',
    '.hpp',
    '.hxx'
}

INCLUDED_FILE_NAMES = {
    'README'
}

EXCLUDED_FILE_NAME_PREFIXESS = [
    '.'
]

EXCLUDED_DIRECTORIES = {
    'build',
    '__pycache__'
}

def make_slickedit_files_section(fdpath_to_scan='./', _folder_name=None, _indent_depth=1):
    fdpath_to_scan = Path(fdpath_to_scan)
    if _folder_name is None:
        opener = '{}<Files AutoFolders="DirectoryView">'.format('\t'*_indent_depth)
        closer = '{}</Files>'.format('\t'*_indent_depth)
    else:
        opener = '{}<Folder Name="{}">'.format('\t'*_indent_depth, _folder_name)
        closer = '{}</Folder>'.format('\t'*_indent_depth)
    fpaths = []
    entries = []
    for fdpath in sorted(fdpath_to_scan.glob('*')):
        if fdpath.is_dir() and not fdpath.name in EXCLUDED_DIRECTORIES:
            entries.extend(make_slickedit_files_section(fdpath, fdpath.name, _indent_depth+1))
        elif fdpath.name in INCLUDED_FILE_NAMES or \
             ''.join(fdpath.suffixes) in INCLUDED_FILE_EXTENSIONS and not any((fdpath.name.startswith(exluded) for exluded in EXCLUDED_FILE_NAME_PREFIXESS)):
            fpaths.append(fdpath)
    entries.extend(('{}<F N="{}"/>'.format('\t'*(_indent_depth+1), str(fpath)) for fpath in fpaths))
    if entries or _folder_name is None:
        return [opener] + entries + [closer]
    else:
        return []

if __name__ == '__main__':
    print('\n'.join(make_slickedit_files_section()))