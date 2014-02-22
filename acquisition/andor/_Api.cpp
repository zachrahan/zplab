// Copyright 2014 WUSTL ZPLAB

#include <iostream>
#include <string>

#include "_Api.h"

std::unique_ptr<_Api> _Api::s_instance;

_Api::_Api()
{
    std::cerr << "_Api::_Api()\n";
    if(AT_InitialiseLibrary() != AT_SUCCESS)
    {
        throw std::string("Failed to initialize Andor SDK3 API (AT_InitialiseLibrary() != AT_SUCCESS).");
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

