// Copyright 2014 WUSTL ZPLAB

#include <boost/python.hpp>
#include <boost/python/import.hpp>
#include <boost/python/module.hpp>
#include <boost/python/class.hpp>
#include <boost/python/manage_new_object.hpp>
#include <iostream>
#include <memory>

#include "_Api.h"
#include "_Camera.h"

using namespace boost::python;

static void stringToAndorExceptionTranslator(const std::shared_ptr<object>& andorExceptionType, const std::string& description)
{
    // The following line is roughly equivalent to the python "andorException = AndorException(description)"
    object andorException{ (*andorExceptionType)(description.c_str()) };
    PyErr_SetObject(andorExceptionType->ptr(), andorException.ptr() );
}

static void test()
{
    throw std::string("testing exceptions");
}

// Note that this block is executed by the Python interpreter when this module is loaded
BOOST_PYTHON_MODULE(_andor)
{
    try
    {
        // Initialize interpreter so that Python code can be executed from C++ and so that C++ code may otherwise access
        // the CPython API
        Py_Initialize();

        // Import our Python exception module
        object andorExceptionPackage{import("acquisition.andor.andor_exception")};
        // Get our exception class type from the module.  Note that the lambda below should be able to capture a
        // boost::python::object directly such that the object is retained while an instance of the lambda exists.  For
        // whatever reason, the captured boost::python::object does not retain its python object, and so the shared_ptr
        // mechanism is instead used to manage the boost::python::object's lifetime and therefore the lifetime of the
        // python object itself.
        std::shared_ptr<object> andorExceptionType{ new object(andorExceptionPackage.attr("AndorException")) };
        // Register the C++ string exception to Python AndorException translator
        register_exception_translator<std::string>( [=](const std::string& description){stringToAndorExceptionTranslator(andorExceptionType, description);} );

        // Initialize Andor SDK3 API library
        _Api::instantiate();

        def("test", test);
    }
    catch(error_already_set const&)
    {
        std::cerr << "Error during initialization of acquisition.andor._andor C++ module:\n";
        PyErr_Print();
        Py_Exit(-1);
    }
}
