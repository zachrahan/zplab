// Copyright 2014 WUSTL ZPLAB

#include "_common.h"
#include "_GilScopedRelease.h"

_GilScopedRelease::_GilScopedRelease()
  : m_pyThreadState(PyEval_SaveThread())
{
}

_GilScopedRelease::~_GilScopedRelease()
{
    PyEval_RestoreThread(m_pyThreadState);
}
