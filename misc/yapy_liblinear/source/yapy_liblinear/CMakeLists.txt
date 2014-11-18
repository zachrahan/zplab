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

add_library(yapy_liblinear SHARED LinearClassifier.cpp
                                  yapy_liblinear_module.cpp
                                  ${PYCXX_SOURCE_DIR}/IndirectPythonInterface.cxx
                                  ${PYCXX_SOURCE_DIR}/cxx_extensions.cxx
                                  ${PYCXX_SOURCE_DIR}/cxxextensions.c
                                  ${PYCXX_SOURCE_DIR}/cxxsupport.cxx)

target_link_libraries(yapy_liblinear liblinear
                                     ${PYTHON_LIBRARIES})

get_target_property(_PYTHON_MODULE_LOCATION yapy_liblinear LOCATION)
if(WIN32)
    string(REPLACE "/" "\\" _PYTHON_MODULE_LOCATION ${_PYTHON_MODULE_LOCATION})
    string(REPLACE "/" "\\" _PROJECT_SOURCE_DIR ${PROJECT_SOURCE_DIR})
    add_custom_command(TARGET yapy_liblinear
                       POST_BUILD
                       COMMAND copy /Y ${_PYTHON_MODULE_LOCATION} "${_PROJECT_SOURCE_DIR}\\yapy_liblinear.pyd")
    unset(_PROJECT_SOURCE_DIR)
else()
    add_custom_command(TARGET yapy_liblinear
                       POST_BUILD
                       COMMAND cp -fv ${_PYTHON_MODULE_LOCATION} "${PROJECT_SOURCE_DIR}/yapy_liblinear.so")
endif()
unset(_PYTHON_MODULE_LOCATION)
