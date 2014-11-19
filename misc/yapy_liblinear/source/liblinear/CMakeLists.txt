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
# Authors: Erik Hvatum <ice.rikh@gmail.com>

add_library(liblinear STATIC liblinear_git/linear.cpp
                             liblinear_git/tron.cpp
                             liblinear_git/blas/daxpy.c
                             liblinear_git/blas/ddot.c
                             liblinear_git/blas/dnrm2.c
                             liblinear_git/blas/dscal.c)
# Obviously the static lib, liblinear.a, as such is not going to be linked against any libraries.
# target_link_libraries does more than set -llibs, however.  It also adds the #defines and other compiler
# flags needed, including (vitally) -fPIC.  Going about this any other way causes CMake to officiously
# add a -fPIE flag because this is a static lib and static libs are only ever linked to executables,
# by CMake's logic.  But, THIS static lib is NOT being linked into an executable!  It is being linked
# into a .so file, and that means we must have -fPIC.
target_link_libraries(liblinear "")

