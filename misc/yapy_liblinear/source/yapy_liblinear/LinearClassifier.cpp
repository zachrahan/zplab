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

#include <memory>
#include <string>
#include <sstream>
#include <Python.h>
#define NPY_NO_DEPRECATED_API NPY_1_7_API_VERSION
#define PY_ARRAY_UNIQUE_SYMBOL yapy_liblinear_ARRAY_API
#define NO_IMPORT_ARRAY
#include <numpy/arrayobject.h>

#include "LinearClassifier.h"

LinearClassifier::LinearClassifier(Py::PythonClassInstance *self, Py::Tuple &args, Py::Dict &kwds)
  : Py::PythonClass<LinearClassifier>::PythonClass(self, args, kwds),
    m_model(nullptr)
{
    std::cout << "LinearClassifier c'tor Called with " << args.length() << " normal arguments." << std::endl;
    Py::List names( kwds.keys() );
    std::cout << "and with " << names.length() << " keyword arguments:" << std::endl;
    for( Py::List::size_type i=0; i< names.length(); i++ )
    {
        Py::String name( names[i] );
        std::cout << "    " << name << std::endl;
    }
}

LinearClassifier::~LinearClassifier()
{
    if(m_model)
    {
        free_and_destroy_model(&m_model);
        m_model = nullptr;
    }
    std::cout << "~LinearClassifier" << std::endl;
}

void LinearClassifier::init_type()
{
    behaviors().name("LinearClassifier");
    behaviors().doc("Python wrapper class around C++ wrapper class around liblinear.");
    behaviors().supportGetattro();
    behaviors().supportSetattro();
    PYCXX_ADD_VARARGS_METHOD(save, save, "save(model_fn) -> None");
    PYCXX_ADD_VARARGS_METHOD(load, load, "load(model_fn) -> None");
    PYCXX_ADD_NOARGS_METHOD(feature_count, feature_count, "feature_count() -> int");
    PYCXX_ADD_NOARGS_METHOD(label_count, label_count, "label_count() -> int");
    PYCXX_ADD_VARARGS_METHOD(get_labels, get_labels, "get_labels(as_view=False) -> numpy.array(dtype=numpy.int)\n"
                                                     "If True is supplied for as_view, a numpy view of data\n"
                                                     "associated with this instance's model is returned, and when this\n"
                                                     "instance or its model is destroyed, that view becomes invalid, and\n"
                                                     "attempting to access it will result in a segfault.");
    PYCXX_ADD_VARARGS_METHOD(train, train, "train(vectors, labels) -> None");
    PYCXX_ADD_VARARGS_METHOD(classify_one_vector, classify_one_vector, "classify_one_vector(vector) -> int\n"
                                                                       "Computes and returns classification for a single feature vector.");

    behaviors().readyType();
}

Py::Object LinearClassifier::getattro(const Py::String &name_)
{
    return genericGetAttro(name_);
}

int LinearClassifier::setattro(const Py::String &name_, const Py::Object &value)
{
    return genericSetAttro(name_, value);
}

void LinearClassifier::check_model(const char* func_name, const char* message) const
{
    if(!m_model)
    {
        if(message)
        {
            throw Py::RuntimeError(message);
        }
        else
        {
            std::string e("A model must be loaded or created before calling ");
            e += func_name;
            e += '.';
            throw Py::RuntimeError(e.c_str());
        }
    }
}

Py::Object LinearClassifier::save(const Py::Tuple& args) const
{
    check_model(nullptr, "No model to save (load a model with load(..) or create one with train(..) "
                         "before attempting to save(..).");
    Py::String model_fn(args[0]);
    std::string model_fn_stdstr(model_fn);
    if(save_model(model_fn_stdstr.c_str(), m_model))
    {
        std::string e("Failed to save model to \"");
        e += model_fn_stdstr;
        e += "\".";
        throw Py::RuntimeError(e.c_str());
    }
    return Py::None();
}

Py::Object LinearClassifier::load(const Py::Tuple& args)
{
    if(m_model)
    {
        free_and_destroy_model(&m_model);
        m_model = nullptr;
    }
    Py::String model_fn(args[0]);
    std::string model_fn_stdstr(model_fn);
    m_model = load_model(model_fn_stdstr.c_str());
    if(!m_model)
    {
        std::string e("Failed to load model from \"");
        e += model_fn_stdstr;
        e += "\".";
        throw Py::RuntimeError(e.c_str());
    }
    return Py::None();
}

Py::Long LinearClassifier::feature_count() const
{
    check_model("feature_count()");
    return Py::Long(m_model->nr_feature);
}

Py::Long LinearClassifier::label_count() const
{
    check_model("label_count()");
    return Py::Long(m_model->nr_class);
}

Py::Object LinearClassifier::get_labels(const Py::Tuple& args) const
{
    check_model("get_labels(..)");

    bool as_view{false};
    if(args.length())
    {
        as_view = args[0].isTrue();
    }

    npy_intp shape(m_model->nr_class);
    if(as_view)
    {
        return Py::asObject(PyArray_SimpleNewFromData(1, &shape, NPY_INT, m_model->label));
    }
    else
    {
        Py::Object ndarray(PyArray_EMPTY(1, &shape, NPY_INT, false), true);
        memcpy(PyArray_GETPTR1(reinterpret_cast<PyArrayObject*>(*ndarray), 0),
               m_model->label,
               sizeof(int) * m_model->nr_class);
        return ndarray;
    }
}

Py::Object LinearClassifier::train(const Py::Tuple& args)
{
    if(args.length() != 2)
    {
        throw Py::RuntimeError("Incorrect number of arguments (2 required).");
    }

    PyObject* vectors_{PyArray_FromAny(*args[0], PyArray_DescrFromType(NPY_DOUBLE), 2, 2, NPY_ARRAY_CARRAY_RO, nullptr)};
    if(!vectors_)
    {
        throw Py::ValueError("Failed to convert vectors argument into 2d numpy double (64-bit float) array.");
    }
    Py::Object vectors(vectors_, true);

    PyObject* labels_{PyArray_FromAny(*args[1], PyArray_DescrFromType(NPY_INT), 1, 1, NPY_ARRAY_CARRAY_RO, nullptr)};
    if(!labels_)
    {
        throw Py::ValueError("Failed to convert labels argument into numpy cint array.");
    }
    Py::Object labels(labels_, true);

    npy_intp vectors_size{PyArray_DIM(reinterpret_cast<PyArrayObject*>(*vectors), 0)};
    npy_intp vector_cardinality{PyArray_DIM(reinterpret_cast<PyArrayObject*>(*vectors), 1)};
    npy_intp labels_size{PyArray_SIZE(reinterpret_cast<PyArrayObject*>(*labels))};
    if(vectors_size != labels_size)
    {
        throw Py::ValueError("len(vectors) != len(labels)");
    }

    std::unique_ptr<feature_node*[]> feature_nodes_ptrs(new feature_node*[vectors_size]);
    std::unique_ptr<feature_node[]> feature_nodes(new feature_node[vectors_size * vector_cardinality + vectors_size]);
    std::unique_ptr<double[]> labels_d(new double[vectors_size]);
    int idx;
    feature_node** feature_node_ptr(feature_nodes_ptrs.get());
    feature_node** feature_nodes_ptrs_end(feature_nodes_ptrs.get() + vectors_size);
    feature_node* feature_node(feature_nodes.get());
    double* vector_element(reinterpret_cast<double*>(PyArray_DATA(reinterpret_cast<PyArrayObject*>(*vectors))));
    double* label_d(labels_d.get());
    int* label(reinterpret_cast<int*>(PyArray_DATA(reinterpret_cast<PyArrayObject*>(*labels))));
    for(; feature_node_ptr != feature_nodes_ptrs_end; ++feature_node_ptr, ++label, ++label_d)
    {
        *feature_node_ptr = feature_node;
        for(idx = 1; idx <= vector_cardinality; ++idx, ++feature_node, ++vector_element)
        {
            feature_node->index = idx;
            feature_node->value = *vector_element;
        }
        (feature_node++)->index = -1;
        *label_d = *label;
    }

    parameter param;
    param.solver_type = L2R_L2LOSS_SVC_DUAL;
    param.C = 1;
    param.eps = 0.1;
    param.p = 0.1;
    param.nr_weight = 0;
    param.weight_label = nullptr;
    param.weight = nullptr;

    problem prob;
    prob.n = vector_cardinality;
    prob.l = vectors_size;
    prob.bias = -1;
    prob.y = labels_d.get();
    prob.x = feature_nodes_ptrs.get();

    model* model_(::train(&prob, &param));
    if(!model_)
    {
        throw Py::RuntimeError("Failed to make model.");
    }

    if(m_model)
    {
        free_and_destroy_model(&m_model);
        m_model = nullptr;
    }

    m_model = model_;

    return Py::None();
}

Py::Object LinearClassifier::classify_one_vector(const Py::Tuple& args) const
{
    if(args.length() != 1)
    {
        throw Py::RuntimeError("Incorrect number of arguments (1 required).");
    }
    check_model("classify_one_vector(..)");

    PyObject* vector_{PyArray_FromAny(*args[0], PyArray_DescrFromType(NPY_DOUBLE), 1, 1, NPY_ARRAY_CARRAY_RO, nullptr)};
    if(!vector_)
    {
        throw Py::ValueError("Failed to convert vectors argument into 1d numpy double (64-bit float) array.");
    }
    Py::Object vector(vector_, true);

    npy_intp vector_size{PyArray_SIZE(reinterpret_cast<PyArrayObject*>(*vector))};
    if(vector_size != m_model->nr_feature)
    {
        std::ostringstream o;
        o << "vector argument has wrong cardinality (has " << vector_size << " elements, but exactly ";
        o << m_model->nr_feature << " are required.";
        std::string s(o.str());
        throw Py::ValueError(s.c_str());
    }

    std::unique_ptr<feature_node[]> feature_nodes(new feature_node[vector_size + 1]);
    int idx{1};
    double* vector_element(reinterpret_cast<double*>(PyArray_DATA(reinterpret_cast<PyArrayObject*>(*vector))));
    feature_node *f_node{feature_nodes.get()};
    feature_node *feature_nodes_end{feature_nodes.get() + vector_size};
    for(; f_node != feature_nodes_end; ++f_node, ++idx, ++vector_element)
    {
        f_node->index = idx;
        f_node->value = *vector_element;
    }
    f_node->index = -1;

    return Py::Long((int)::predict(m_model, feature_nodes.get()));
}

