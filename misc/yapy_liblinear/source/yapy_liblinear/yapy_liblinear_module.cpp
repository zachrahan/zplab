// The MIT License (MIT)
// 
// Copyright (c) 2014 WUSTL ZPLAB
// 
// Permission is hereby granted, free of charge, to any person obtaining a copy
// of this software and associated documentation files (the "Software"), to deal
// in the Software without restriction, including without limitation the rights
// to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
// copies of the Software, and to permit persons to whom the Software is
// furnished to do so, subject to the following conditions:
// 
// The above copyright notice and this permission notice shall be included in all
// copies or substantial portions of the Software.
// 
// THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
// IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
// FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
// AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
// LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
// OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
// SOFTWARE.
// 
// Authors: Erik Hvatum <ice.rikh@gmail.com>

#include <Python.h>
#define NPY_NO_DEPRECATED_API NPY_1_7_API_VERSION
#define PY_ARRAY_UNIQUE_SYMBOL yapy_liblinear_ARRAY_API
#include <numpy/arrayobject.h>

#include "CXX/Objects.hxx"
#include "CXX/Extensions.hxx"

#include "LinearClassifier.h"

class yapy_liblinear_module
  : public Py::ExtensionModule<yapy_liblinear_module>
{
public:
    yapy_liblinear_module()
      : Py::ExtensionModule<yapy_liblinear_module>("yapy_liblinear")
    {
        LinearClassifier::init_type();

        initialize("yapy_liblinear (Yet Another Python liblinear interface)");

        Py::Dict mod_dict(moduleDictionary());
        Py::Object cls_LinearClassifier(LinearClassifier::type());
        mod_dict["LinearClassifier"] = cls_LinearClassifier;
    }

    virtual ~yapy_liblinear_module()
    {}
};

#if defined(_WIN32)
#define EXPORT_SYMBOL __declspec(dllexport)
#else
#define EXPORT_SYMBOL
#endif

extern "C" EXPORT_SYMBOL PyObject *PyInit_yapy_liblinear()
{
#if defined(PY_WIN32_DELAYLOAD_PYTHON_DLL)
    Py::InitialisePythonIndirectPy::Interface();
#endif

    import_array();
    static yapy_liblinear_module* m{new yapy_liblinear_module()};
    return m->module().ptr();
}

#if defined(_WIN32)
#define EXPORT_SYMBOL __declspec(dllexport)
#else
#define EXPORT_SYMBOL
#endif

// symbol required for the debug version
extern "C" EXPORT_SYMBOL PyObject *PyInit_yapy_liblinear_d()
{ 
    return PyInit_yapy_liblinear();
}

