// Copyright 2014 WUSTL ZPLAB

#pragma once
#include "_common.h"

class _GilScopedRelease
  : boost::noncopyable
{
public:
    _GilScopedRelease();
    ~_GilScopedRelease();
private:
    PyThreadState* m_pyThreadState;
};
