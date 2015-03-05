// The MIT License (MIT)
// 
// Copyright (c) 2014-2015 WUSTL ZPLAB
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

#include <string>
#include <map>

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
    Py::Object get_parameters() const;
    PYCXX_NOARGS_METHOD_DECL(LinearClassifier, get_parameters)
    Py::Object set_parameters(const Py::Tuple& args);
    PYCXX_VARARGS_METHOD_DECL(LinearClassifier, set_parameters)
    Py::Object get_solvers() const;
    PYCXX_NOARGS_METHOD_DECL(LinearClassifier, get_solvers)
    Py::Object get_w(const Py::Tuple& args) const;
    PYCXX_VARARGS_METHOD_DECL(LinearClassifier, get_w)

    Py::Object train(const Py::Tuple& args);
    PYCXX_VARARGS_METHOD_DECL(LinearClassifier, train)

    Py::Object classify_one_vector(const Py::Tuple& args) const;
    PYCXX_VARARGS_METHOD_DECL(LinearClassifier, classify_one_vector)
    Py::Object classify(const Py::Tuple& args) const;
    PYCXX_VARARGS_METHOD_DECL(LinearClassifier, classify)

protected:
    model* m_model;
    // Used for holding parameters when there is no model (in order that the user may set parameters and then call train 
    // to generate a model). 
    parameter* m_staged_param;
    double* m_staged_bias;

    static const std::map<std::string, int> sm_solver_names_to_idxs;

    void check_model(const char* func_name, const char* message=nullptr) const;
    void make_default_staged_param_and_bias();
};

