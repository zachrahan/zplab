// Copyright 2014 WUSTL ZPLAB

#include "_common.h"
#include "_AndorException.h"
#include "_Api.h"

std::unique_ptr<_Api> _Api::s_instance;

_Api::_Api()
{
    std::cerr << "_Api::_Api()\n";
    int r = AT_InitialiseLibrary();
    if(r != AT_SUCCESS)
    {
        throw _AndorException("Failed to initialize Andor SDK3 API.", r);
    }
}

_Api::~_Api()
{
    std::cerr << "_Api::~_Api()\n";
    if(AT_FinaliseLibrary() != AT_SUCCESS)
    {
        std::cerr << "Note: call to finalize Andor SDK3 API failed (AT_FinaliseLibrary() != AT_SUCCESS).\n";
    }
}

void _Api::instantiate()
{
    if(s_instance)
    {
        throw std::string("_Api::instantiate() called more than once.");
    }
    s_instance.reset(new _Api);
}

