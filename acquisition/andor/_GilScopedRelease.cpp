// Copyright 2014 WUSTL ZPLAB

#include "_common.h"
#include "_AndorException.h"
#include "_GilScopedRelease.h"

_GilScopedRelease::_GilScopedRelease()
  : m_pyThreadState(PyEval_SaveThread())
{
//  std::cerr << "_GilScopedRelease::_GilScopedRelease()\n";
    if(m_pyThreadState == nullptr)
    {
        throw _AndorExceptionBase("_GilScopedRelease(): PyEval_SaveThread returned null.");
    }
}

_GilScopedRelease::~_GilScopedRelease()
{
//  std::cerr << "_GilScopedRelease::~_GilScopedRelease()\n";
    PyEval_RestoreThread(m_pyThreadState);
}
