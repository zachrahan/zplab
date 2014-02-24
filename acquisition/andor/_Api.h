// Copyright 2014 WUSTL ZPLAB

#pragma once
#include "_common.h"

// Used to execute AT_InitialiseLibrary()/AT_FinaliseLibrary() when python loads/unloads the _andor module
class _Api
{
public:
    _Api();
    ~_Api();

    static void instantiate();

private:
    static std::unique_ptr<_Api> s_instance;
};

