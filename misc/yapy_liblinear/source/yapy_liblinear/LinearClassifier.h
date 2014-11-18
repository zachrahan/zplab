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

#pragma once

#include "CXX/Objects.hxx"
#include "CXX/Extensions.hxx"

#include "../liblinear/liblinear_git/linear.h"

class LinearClassifier
  : public Py::PythonClass<LinearClassifier>
{
public:
    LinearClassifier(Py::PythonClassInstance *self, Py::Tuple &args, Py::Dict &kwds);
    virtual ~LinearClassifier();

    static void init_type();

    Py::Object getattro(const Py::String &name_);
    int setattro(const Py::String &name_, const Py::Object &value);

    Py::Object save(const Py::Tuple& args) const;
    PYCXX_VARARGS_METHOD_DECL(LinearClassifier, save)
    Py::Object load(const Py::Tuple& args);
    PYCXX_VARARGS_METHOD_DECL(LinearClassifier, load)

    Py::Long feature_count() const;
    PYCXX_NOARGS_METHOD_DECL(LinearClassifier, feature_count)
    Py::Long label_count() const;
    PYCXX_NOARGS_METHOD_DECL(LinearClassifier, label_count)
    Py::Object get_labels(const Py::Tuple& args) const;
    PYCXX_VARARGS_METHOD_DECL(LinearClassifier, get_labels)

    Py::Object train(const Py::Tuple& args);
    PYCXX_VARARGS_METHOD_DECL(LinearClassifier, train)

protected:
    model* m_model;

    void check_model(const char* func_name, const char* message=nullptr) const;
};

