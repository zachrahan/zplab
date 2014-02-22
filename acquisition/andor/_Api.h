// Copyright 2014 WUSTL ZPLAB

#include <atcore.h>
#include <memory>

// Used to execute AT_InitialiseLibrary()/AT_FinaliseLibrary() when python loads/unloads this module
class _Api
{
public:
    _Api();
    ~_Api();

    static void instantiate();

private:
    static std::unique_ptr<_Api> s_instance;
};

