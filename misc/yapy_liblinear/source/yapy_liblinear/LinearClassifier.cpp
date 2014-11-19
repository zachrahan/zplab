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

#include <algorithm>
#include <iostream>
#include <memory>
#include <sstream>
#include <vector>
#include <Python.h>
#define NPY_NO_DEPRECATED_API NPY_1_7_API_VERSION
#define PY_ARRAY_UNIQUE_SYMBOL yapy_liblinear_ARRAY_API
#define NO_IMPORT_ARRAY
#include <numpy/arrayobject.h>

#include "LinearClassifier.h"

const std::map<std::string, int> LinearClassifier::sm_solver_names_to_idxs;

LinearClassifier::LinearClassifier(Py::PythonClassInstance *self, Py::Tuple &args, Py::Dict &kwds)
  : Py::PythonClass<LinearClassifier>::PythonClass(self, args, kwds),
    m_model(nullptr),
    m_staged_param(nullptr)
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
        destroy_param(&m_model->param);
        free_and_destroy_model(&m_model);
        m_model = nullptr;
    }
    if(m_staged_param)
    {
        destroy_param(m_staged_param);
        delete m_staged_param;
        m_staged_param = nullptr;
    }
    std::cout << "~LinearClassifier" << std::endl;
}

void LinearClassifier::init_type()
{
    std::map<std::string, int>& sntis(const_cast<std::map<std::string, int>&>(sm_solver_names_to_idxs));
    std::map<std::string, int>::iterator sntis_it;
    std::string sn;
    int si{0};
    for(const char** snp{solver_type_table}; *snp; ++snp, ++si)
    {
        sn = *snp;
        if(!sn.empty())
        {
            sntis_it = sntis.find(sn);
            if(sntis_it != sntis.end())
            {
                std::string e("liblinear solver name \"");
                e += sn;
                e += "\" appears more than once in liblinear's solver_type_table.";
                std::cerr << e << std::endl;
                throw e;
            }
            sntis[sn] = si;
        }
    }

    behaviors().name("LinearClassifier");
    behaviors().doc("Python wrapper class around C++ wrapper class around liblinear C wrapper around liblinear C++ implementation.");
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
    PYCXX_ADD_NOARGS_METHOD(get_parameters, get_parameters, "get_parameters() -> dict");
    PYCXX_ADD_VARARGS_METHOD(set_parameters, set_parameters, "set_parameters(dict) -> None\n"
                                                             "Supply a dict of label : weight values for weights, or None, or an empty\n"
                                                             "dict for weights if no weights are desired.");
    PYCXX_ADD_NOARGS_METHOD(get_solvers, get_solvers, "get_solvers() -> list\n"
                                                      "Returns a list containing the names of the available solvers.");

    behaviors().readyType();
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

void LinearClassifier::make_default_staged_param()
{
    if(m_staged_param)
    {
        // Delete weights
        destroy_param(m_staged_param);
    }
    else
    {
        m_staged_param = new parameter;
    }
    m_staged_param->solver_type = L2R_L2LOSS_SVC_DUAL;
    m_staged_param->C = 1;
    m_staged_param->eps = 0.1;
    m_staged_param->p = 0.1;
    m_staged_param->nr_weight = 0;
    m_staged_param->weight_label = nullptr;
    m_staged_param->weight = nullptr;
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
        destroy_param(&m_model->param);
        free_and_destroy_model(&m_model);
        m_model = nullptr;
    }
    if(m_staged_param)
    {
        destroy_param(m_staged_param);
        delete m_staged_param;
        m_staged_param = nullptr;
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

Py::Object LinearClassifier::get_parameters() const
{
    const parameter* param;
    if(m_model)
    {
        param = &m_model->param;
    }
    else
    {
        if(!m_staged_param)
        {
            const_cast<LinearClassifier*>(this)->make_default_staged_param();
        }
        param = m_staged_param;
    }

    Py::Dict ret;
    ret["solver"] = Py::String(solver_type_table[param->solver_type]);
    ret["eps"] = Py::Float(param->eps);
    ret["C"] = Py::Float(param->C);
    ret["p"] = Py::Float(param->p);
    Py::Dict weights;
    ret["weights"] = weights;
    if(param->nr_weight > 0)
    {
        int* wl{param->weight_label};
        int*const wl_end{wl + param->nr_weight};
        double* w{param->weight};
        for(; wl != wl_end; ++wl, ++w)
        {
            weights[Py::Long(*wl)] = Py::Float(*w);
        }
    }
    return ret;
}

Py::Object LinearClassifier::set_parameters(const Py::Tuple& args)
{
    if(args.length() != 1)
    {
        throw Py::RuntimeError("Incorrect number of arguments (1 required).");
    }
    parameter* param;
    if(m_model)
    {
        param = &m_model->param;
    }
    else
    {
        if(!m_staged_param)
        {
            make_default_staged_param();
        }
        param = m_staged_param;
    }
    Py::Dict param_dict(args[0]);
    Py::List param_items(param_dict.items());
    std::string pname;
    Py::Tuple param_item;
    Py::String pname_;
    for(auto param_item_it = param_items.begin(); param_item_it != param_items.end(); ++param_item_it)
    {
        param_item = *param_item_it;
        pname_ = param_item[0];
        pname = pname_.as_std_string("utf-8");
        if(pname == "solver")
        {
            Py::String solver_(param_item[1]);
            std::string solver(solver_.as_std_string("utf-8"));
            std::map<std::string, int>::const_iterator sntis_it(sm_solver_names_to_idxs.find(solver));
            if(sntis_it == sm_solver_names_to_idxs.end())
            {
                std::string e("Unknown solver name \"");
                e += solver;
                e += "\" specified.  Call .get_solvers() to get the list of supported solver names.";
                throw Py::KeyError(e.c_str());
            }
            param->solver_type = sntis_it->second;
        }
        else if(pname == "weights")
        {
            if(param_item[1].isTrue())
            {
                Py::Dict weights(param_item[1]);
                Py::List weights_items(weights.items());
                Py::Tuple weights_item;
                std::vector<std::pair<int, double>> putative_weights;
                for(auto weights_item_it = weights_items.begin(); weights_item_it != weights_items.end(); ++weights_item_it)
                {
                    weights_item = *weights_item_it;
                    Py::Long label(weights_item[0]);
                    Py::Float weight(weights_item[1]);
                    putative_weights.emplace_back(static_cast<int>(label), static_cast<double>(weight));
                }
                destroy_param(param);
                param->nr_weight = static_cast<int>(putative_weights.size());
                param->weight_label = reinterpret_cast<int*>(calloc(putative_weights.size(), sizeof(int)));
                param->weight = reinterpret_cast<double*>(calloc(putative_weights.size(), sizeof(double)));
                int* weight_label_it{param->weight_label};
                int* weight_label_end{weight_label_it + putative_weights.size()};
                double* weight_it{param->weight};
                auto putative_weights_it = putative_weights.begin();
                for(; weight_label_it != weight_label_end; ++weight_label_it, ++weight_it, ++putative_weights_it)
                {
                    *weight_label_it = putative_weights_it->first;
                    *weight_it = putative_weights_it->second;
                }
            }
            else
            {
                destroy_param(param);
            }
        }
        else if(pname == "eps")
        {
            param->eps = Py::Float(param_item[1]);
        }
        else if(pname == "C")
        {
            param->C = Py::Float(param_item[1]);
        }
        else if(pname == "p")
        {
            param->p = Py::Float(param_item[1]);
        }
        else
        {
            std::string e("Unkown parameter name \"");
            e += pname;
            e += "\" specified.  Refer to output of .get_solvers() for a list of supported parameter names.";
            throw Py::KeyError(e.c_str());
        }
    }
    return Py::None();
}

Py::Object LinearClassifier::get_solvers() const
{
    Py::List ret;
    std::string sn;
    for(const char** snp{solver_type_table}; *snp; ++snp)
    {
        sn = *snp;
        if(!sn.empty())
        {
            ret.append(Py::String(sn));
        }
    }
    return ret;
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

    problem prob;
    prob.n = vector_cardinality;
    prob.l = vectors_size;
    prob.bias = -1;
    prob.y = labels_d.get();
    prob.x = feature_nodes_ptrs.get();

//  model* model_(::train(&prob, &param));
//  if(!model_)
//  {
//      throw Py::RuntimeError("Failed to make model.");
//  }
// 
//  if(m_model)
//  {
//      destroy_param(&m_model->param);
//      free_and_destroy_model(&m_model);
//      m_model = nullptr;
//  }
// 
//  m_model = model_;

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

