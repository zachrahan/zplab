// Copyright 2014 WUSTL ZPLAB

#include "_common.h"
#include "_AndorException.h"
#include "_Camera.h"

// template<typename T>
// struct DeleteWatcher
// {
//     std::string name;
//     explicit DeleteWatcher(const std::string& name_) : name(name_) {}
//     void operator () (T* p)
//     {
//         std::cerr << "DELETING " << name << std::endl;
//         delete p;
//     }
// };

std::shared_ptr<std::vector<std::string>> _Camera::getDeviceNames()
{
    AT_64 deviceCount;
    int r = AT_GetInt(AT_HANDLE_SYSTEM, L"Device Count", &deviceCount);
    if(r != AT_SUCCESS)
    {
        throw _AndorException("Failed to get Andor device count.", r);
    }
    if(r < 0)
    {
        throw _AndorExceptionBase("Andor API returned a negative value for device count.");
    }
//  std::shared_ptr<std::vector<std::string>> ret(new std::vector<std::string>, DeleteWatcher<std::vector<std::string>>("device name vector"));
    std::shared_ptr<std::vector<std::string>> ret(new std::vector<std::string>);
    if(deviceCount > 0)
    {
        ret->reserve(static_cast<std::size_t>(deviceCount));
        wchar_t buff[257];
        AT_H handle;
        for(int deviceIndex(0); deviceIndex != deviceCount; ++deviceIndex)
        {
            r = AT_Open(deviceIndex, &handle);
            if(r != AT_SUCCESS)
            {
                std::ostringstream o;
                o << "Failed to open Andor device with index " << deviceIndex << '.';
                throw _AndorException(o.str(), r);
            }
            r = AT_GetString(handle, L"Camera Model", buff, 256);
            // Ensure that buff is null terminated
            buff[256] = L'\0';
            ret->push_back(boost::locale::conv::utf_to_utf<char>(buff));
            r = AT_Close(handle);
            if(r != AT_SUCCESS)
            {
                std::ostringstream o;
                o << "Failed to close Andor device with index " << deviceIndex << '.';
                throw _AndorException(o.str(), r);
            }
        }
    }
    return ret;
}
