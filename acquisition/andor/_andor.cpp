// Copyright 2014 WUSTL ZPLAB

#include "_common.h"
#include "_AndorException.h"
#include "_Api.h"
#include "_Camera.h"

using namespace boost::python;

static void andorExceptionBaseTranslator(const std::shared_ptr<object>& andorExceptionType, const _AndorExceptionBase& _andorExceptionBase)
{
    std::cerr << "static void andorExceptionBaseTranslator(const std::shared_ptr<object>& andorExceptionType, const _AndorExceptionBase& _andorExceptionBase)\n";
    // The following line is roughly equivalent to the python "andorException = 
    // AndorException(_andorExceptionBase.description())"
    object andorException{ (*andorExceptionType)(_andorExceptionBase.description().c_str()) };
    PyErr_SetObject(andorExceptionType->ptr(), andorException.ptr() );
}

static void andorExceptionTranslator(const std::shared_ptr<object>& andorExceptionType, const _AndorException& _andorException)
{
    std::cerr << "static void andorExceptionTranslator(const std::shared_ptr<object>& andorExceptionType, const _AndorException& _andorException)\n";
    // The following line is roughly equivalent to the python "andorException = 
    // AndorException(_andorException.description(), _andorException.errorCode(), _andorException.errorName())"
    object andorException{ (*andorExceptionType)(_andorException.description().c_str(), _andorException.errorCode(), _andorException.errorName().c_str()) };
    PyErr_SetObject(andorExceptionType->ptr(), andorException.ptr() );
}

static std::string test()
{
    return std::string("Héllø ∑ô¡™£¢d!");
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
        // Register C++ to python exception translators
        register_exception_translator<_AndorExceptionBase>( [=](const _AndorExceptionBase& _andorExceptionBase){andorExceptionBaseTranslator(andorExceptionType, _andorExceptionBase);} );
        register_exception_translator<_AndorException>( [=](const _AndorException& _andorException){andorExceptionTranslator(andorExceptionType, _andorException);} );

        // Initialize Andor SDK3 API library
        _Api::instantiate();

        def("test", test);

        class_< std::vector<std::string>, std::shared_ptr<std::vector<std::string>> >("StringVector")
            .def( vector_indexing_suite<std::vector<std::string> >());

        class_<_Camera>("_Camera")
            .def("getDeviceNames", &_Camera::getDeviceNames)
            .staticmethod("getDeviceNames");
    }
    catch(error_already_set const&)
    {
        std::cerr << "Error during initialization of acquisition.andor._andor C++ module:\n";
        PyErr_Print();
        Py_Exit(-1);
    }
}
