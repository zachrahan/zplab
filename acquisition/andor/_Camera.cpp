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
    int r = ::AT_GetInt(AT_HANDLE_SYSTEM, L"Device Count", &deviceCount);
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
        for(AT_64 deviceIndex(0); deviceIndex != deviceCount; ++deviceIndex)
        {
            r = ::AT_Open(deviceIndex, &handle);
            if(r != AT_SUCCESS)
            {
                std::ostringstream o;
                o << "Failed to open Andor device with index " << deviceIndex << '.';
                throw _AndorException(o.str(), r);
            }
            r = ::AT_GetString(handle, L"Camera Model", buff, 256);
            // Ensure that buff is null terminated
            buff[256] = L'\0';
            ret->push_back(boost::locale::conv::utf_to_utf<char>(buff));
            r = ::AT_Close(handle);
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

_Camera::_Camera(const AT_64& deviceIndex)
{
    int r = ::AT_Open(deviceIndex, &m_dh);
    if(r != AT_SUCCESS)
    {
        std::ostringstream o;
        o << "Failed to open Andor device with index " << deviceIndex << '.';
        throw _AndorException(o.str(), r);
    }
    std::cerr << "_Camera::_Camera()\n";
}

_Camera::~_Camera()
{
    int r = ::AT_Close(m_dh);
    if(r != AT_SUCCESS)
    {
        std::string errorName;
        _AndorException::lookupErrorName(r, errorName);
        std::cerr << "WARNING: AT_Close failed with error #" << r << " (" << errorName << ").\n";
    }
    std::cerr << "_Camera::~_Camera()\n";
}

bool _Camera::AT_IsImplemented(const Feature& feature)
{
    std::ptrdiff_t fi{static_cast<std::ptrdiff_t>(feature)};
    AT_BOOL b;
    int r = ::AT_IsImplemented(m_dh, sm_featureNames[fi], &b);
    if(r != AT_SUCCESS)
    {
        std::ostringstream o;
        o << "AT_IsImplemented for feature \"" << boost::locale::conv::utf_to_utf<char>(sm_featureNames[fi]) << "\" failed.";
        throw _AndorException(o.str(), r);
    }
    return b != AT_FALSE;
}

bool _Camera::AT_IsReadable(const Feature& feature)
{
    std::ptrdiff_t fi{static_cast<std::ptrdiff_t>(feature)};
    AT_BOOL b;
    int r = ::AT_IsReadable(m_dh, sm_featureNames[fi], &b);
    if(r != AT_SUCCESS)
    {
        std::ostringstream o;
        o << "AT_IsReadable for feature \"" << boost::locale::conv::utf_to_utf<char>(sm_featureNames[fi]) << "\" failed.";
        throw _AndorException(o.str(), r);
    }
    return b != AT_FALSE;
}

bool _Camera::AT_IsWritable(const Feature& feature)
{
    std::ptrdiff_t fi{static_cast<std::ptrdiff_t>(feature)};
    AT_BOOL b;
    int r = ::AT_IsWritable(m_dh, sm_featureNames[fi], &b);
    if(r != AT_SUCCESS)
    {
        std::ostringstream o;
        o << "AT_IsWritable for feature \"" << boost::locale::conv::utf_to_utf<char>(sm_featureNames[fi]) << "\" failed.";
        throw _AndorException(o.str(), r);
    }
    return b != AT_FALSE;
}

bool _Camera::AT_IsReadOnly(const Feature& feature)
{
    std::ptrdiff_t fi{static_cast<std::ptrdiff_t>(feature)};
    AT_BOOL b;
    int r = ::AT_IsReadOnly(m_dh, sm_featureNames[fi], &b);
    if(r != AT_SUCCESS)
    {
        std::ostringstream o;
        o << "AT_IsReadOnly for feature \"" << boost::locale::conv::utf_to_utf<char>(sm_featureNames[fi]) << "\" failed.";
        throw _AndorException(o.str(), r);
    }
    return b != AT_FALSE;
}

void _Camera::AT_SetInt(const Feature& feature, const AT_64& value)
{
    std::ptrdiff_t fi{static_cast<std::ptrdiff_t>(feature)};
    int r = ::AT_SetInt(m_dh, sm_featureNames[fi], value);
    if(r != AT_SUCCESS)
    {
        std::ostringstream o;
        o << "AT_SetInt with value " << value << " for feature \"" << boost::locale::conv::utf_to_utf<char>(sm_featureNames[fi]) << "\" failed.";
        throw _AndorException(o.str(), r);
    }
}

AT_64 _Camera::AT_GetInt(const Feature& feature)
{
    std::ptrdiff_t fi{static_cast<std::ptrdiff_t>(feature)};
    AT_64 ret;
    int r = ::AT_GetInt(m_dh, sm_featureNames[fi], &ret);
    if(r != AT_SUCCESS)
    {
        std::ostringstream o;
        o << "AT_GetInt for feature \"" << boost::locale::conv::utf_to_utf<char>(sm_featureNames[fi]) << "\" failed.";
        throw _AndorException(o.str(), r);
    }
    return ret;
}

AT_64 _Camera::AT_GetIntMax(const Feature& feature)
{
    std::ptrdiff_t fi{static_cast<std::ptrdiff_t>(feature)};
    AT_64 ret;
    int r = ::AT_GetIntMax(m_dh, sm_featureNames[fi], &ret);
    if(r != AT_SUCCESS)
    {
        std::ostringstream o;
        o << "AT_GetIntMax for feature \"" << boost::locale::conv::utf_to_utf<char>(sm_featureNames[fi]) << "\" failed.";
        throw _AndorException(o.str(), r);
    }
    return ret;
}

AT_64 _Camera::AT_GetIntMin(const Feature& feature)
{
    std::ptrdiff_t fi{static_cast<std::ptrdiff_t>(feature)};
    AT_64 ret;
    int r = ::AT_GetIntMin(m_dh, sm_featureNames[fi], &ret);
    if(r != AT_SUCCESS)
    {
        std::ostringstream o;
        o << "AT_GetIntMin for feature \"" << boost::locale::conv::utf_to_utf<char>(sm_featureNames[fi]) << "\" failed.";
        throw _AndorException(o.str(), r);
    }
    return ret;
}

void _Camera::AT_SetFloat(const Feature& feature, const double& value)
{
    std::ptrdiff_t fi{static_cast<std::ptrdiff_t>(feature)};
    int r = ::AT_SetFloat(m_dh, sm_featureNames[fi], value);
    if(r != AT_SUCCESS)
    {
        std::ostringstream o;
        o << "AT_SetFloat with value " << value << " for feature \"" << boost::locale::conv::utf_to_utf<char>(sm_featureNames[fi]) << "\" failed.";
        throw _AndorException(o.str(), r);
    }
}

double _Camera::AT_GetFloat(const Feature& feature)
{
    std::ptrdiff_t fi{static_cast<std::ptrdiff_t>(feature)};
    double ret;
    int r = ::AT_GetFloat(m_dh, sm_featureNames[fi], &ret);
    if(r != AT_SUCCESS)
    {
        std::ostringstream o;
        o << "AT_GetFloat for feature \"" << boost::locale::conv::utf_to_utf<char>(sm_featureNames[fi]) << "\" failed.";
        throw _AndorException(o.str(), r);
    }
    return ret;
}

double _Camera::AT_GetFloatMax(const Feature& feature)
{
    std::ptrdiff_t fi{static_cast<std::ptrdiff_t>(feature)};
    double ret;
    int r = ::AT_GetFloatMax(m_dh, sm_featureNames[fi], &ret);
    if(r != AT_SUCCESS)
    {
        std::ostringstream o;
        o << "AT_GetFloatMax for feature \"" << boost::locale::conv::utf_to_utf<char>(sm_featureNames[fi]) << "\" failed.";
        throw _AndorException(o.str(), r);
    }
    return ret;
}

double _Camera::AT_GetFloatMin(const Feature& feature)
{
    std::ptrdiff_t fi{static_cast<std::ptrdiff_t>(feature)};
    double ret;
    int r = ::AT_GetFloatMin(m_dh, sm_featureNames[fi], &ret);
    if(r != AT_SUCCESS)
    {
        std::ostringstream o;
        o << "AT_GetFloatMin for feature \"" << boost::locale::conv::utf_to_utf<char>(sm_featureNames[fi]) << "\" failed.";
        throw _AndorException(o.str(), r);
    }
    return ret;
}

void _Camera::AT_SetBool(const Feature& feature, const bool& value)
{
    std::ptrdiff_t fi{static_cast<std::ptrdiff_t>(feature)};
    int r = ::AT_SetBool(m_dh, sm_featureNames[fi], value);
    if(r != AT_SUCCESS)
    {
        std::ostringstream o;
        o << "AT_SetBool with value " << (value ? "True" : "False") << " for feature \"" << boost::locale::conv::utf_to_utf<char>(sm_featureNames[fi]) << "\" failed.";
        throw _AndorException(o.str(), r);
    }
}

bool _Camera::AT_GetBool(const Feature& feature)
{
    std::ptrdiff_t fi{static_cast<std::ptrdiff_t>(feature)};
    AT_BOOL b;
    int r = ::AT_GetBool(m_dh, sm_featureNames[fi], &b);
    if(r != AT_SUCCESS)
    {
        std::ostringstream o;
        o << "AT_GetBool for feature \"" << boost::locale::conv::utf_to_utf<char>(sm_featureNames[fi]) << "\" failed.";
        throw _AndorException(o.str(), r);
    }
    return b != AT_FALSE;
}

void _Camera::AT_SetEnumIndex(const Feature& feature, const int& value)
{
    std::ptrdiff_t fi{static_cast<std::ptrdiff_t>(feature)};
    int r = ::AT_SetEnumIndex(m_dh, sm_featureNames[fi], value);
    if(r != AT_SUCCESS)
    {
        std::ostringstream o;
        o << "AT_SetEnumIndex with index \"" << value << "\" for feature \"" << boost::locale::conv::utf_to_utf<char>(sm_featureNames[fi]) << "\" failed.";
        throw _AndorException(o.str(), r);
    }
}

void _Camera::AT_SetEnumString(const Feature& feature, const std::string& value)
{
    std::ptrdiff_t fi{static_cast<std::ptrdiff_t>(feature)};
    std::wstring s{boost::locale::conv::utf_to_utf<wchar_t>(value)};
    int r = ::AT_SetEnumString(m_dh, sm_featureNames[fi], s.c_str());
    if(r != AT_SUCCESS)
    {
        std::ostringstream o;
        o << "AT_SetEnumString with string \"" << value << "\" for feature \"" << boost::locale::conv::utf_to_utf<char>(sm_featureNames[fi]) << "\" failed.";
        throw _AndorException(o.str(), r);
    }
}

int _Camera::AT_GetEnumIndex(const Feature& feature)
{
    std::ptrdiff_t fi{static_cast<std::ptrdiff_t>(feature)};
    int ret;
    int r = ::AT_GetEnumIndex(m_dh, sm_featureNames[fi], &ret);
    if(r != AT_SUCCESS)
    {
        std::ostringstream o;
        o << "AT_GetEnumIndex for feature \"" << boost::locale::conv::utf_to_utf<char>(sm_featureNames[fi]) << "\" failed.";
        throw _AndorException(o.str(), r);
    }
    return ret;
}

int _Camera::AT_GetEnumCount(const Feature& feature)
{
    std::ptrdiff_t fi{static_cast<std::ptrdiff_t>(feature)};
    int ret;
    int r = ::AT_GetEnumCount(m_dh, sm_featureNames[fi], &ret);
    if(r != AT_SUCCESS)
    {
        std::ostringstream o;
        o << "AT_GetEnumCount for feature \"" << boost::locale::conv::utf_to_utf<char>(sm_featureNames[fi]) << "\" failed.";
        throw _AndorException(o.str(), r);
    }
    return ret;
}

bool _Camera::AT_IsEnumIndexAvailable(const Feature& feature, const int& index)
{
    std::ptrdiff_t fi{static_cast<std::ptrdiff_t>(feature)};
    AT_BOOL b;
    int r = ::AT_IsEnumIndexAvailable(m_dh, sm_featureNames[fi], index, &b);
    if(r != AT_SUCCESS)
    {
        std::ostringstream o;
        o << "AT_IsEnumIndexAvailable with index " << index << " for feature \"" << boost::locale::conv::utf_to_utf<char>(sm_featureNames[fi]) << "\" failed.";
        throw _AndorException(o.str(), r);
    }
    return b != AT_FALSE;
}

bool _Camera::AT_IsEnumIndexImplemented(const Feature& feature, const int& index)
{
    std::ptrdiff_t fi{static_cast<std::ptrdiff_t>(feature)};
    AT_BOOL b;
    int r = ::AT_IsEnumIndexImplemented(m_dh, sm_featureNames[fi], index, &b);
    if(r != AT_SUCCESS)
    {
        std::ostringstream o;
        o << "AT_IsEnumIndexImplemented with index " << index << " for feature \"" << boost::locale::conv::utf_to_utf<char>(sm_featureNames[fi]) << "\" failed.";
        throw _AndorException(o.str(), r);
    }
    return b != AT_FALSE;
}

std::string _Camera::AT_GetEnumStringByIndex(const Feature& feature, const int& index)
{
    std::ptrdiff_t fi{static_cast<std::ptrdiff_t>(feature)};
    wchar_t buff[257];
    int r = ::AT_GetEnumStringByIndex(m_dh, sm_featureNames[fi], index, buff, 256);
    if(r != AT_SUCCESS)
    {
        std::ostringstream o;
        o << "AT_GetEnumStringByIndex with index " << index << " for feature \"" << boost::locale::conv::utf_to_utf<char>(sm_featureNames[fi]) << "\" failed.";
        throw _AndorException(o.str(), r);
    }
    buff[256] = L'\0';
    return boost::locale::conv::utf_to_utf<char>(buff);
}


void _Camera::AT_Command(const Feature& feature)
{
    std::ptrdiff_t fi{static_cast<std::ptrdiff_t>(feature)};
    int r = ::AT_Command(m_dh, sm_featureNames[fi]);
    if(r != AT_SUCCESS)
    {
        std::ostringstream o;
        o << "AT_Command for feature \"" << boost::locale::conv::utf_to_utf<char>(sm_featureNames[fi]) << "\" failed.";
        throw _AndorException(o.str(), r);
    }
}

void _Camera::AT_SetString(const Feature& feature, const std::string& value)
{
    std::ptrdiff_t fi{static_cast<std::ptrdiff_t>(feature)};
    std::wstring s{boost::locale::conv::utf_to_utf<wchar_t>(value)};
    int r = ::AT_SetString(m_dh, sm_featureNames[fi], s.c_str());
    if(r != AT_SUCCESS)
    {
        std::ostringstream o;
        o << "AT_SetString with string \"" << value << "\" for feature \"" << boost::locale::conv::utf_to_utf<char>(sm_featureNames[fi]) << "\" failed.";
        throw _AndorException(o.str(), r);
    }
}

std::string _Camera::AT_GetString(const Feature& feature)
{
    std::ptrdiff_t fi{static_cast<std::ptrdiff_t>(feature)};
    wchar_t buff[257];
    int r = ::AT_GetString(m_dh, sm_featureNames[fi], buff, 256);
    if(r != AT_SUCCESS)
    {
        std::ostringstream o;
        o << "AT_GetString for feature \"" << boost::locale::conv::utf_to_utf<char>(sm_featureNames[fi]) << "\" failed.";
        throw _AndorException(o.str(), r);
    }
    buff[256] = L'\0';
    return boost::locale::conv::utf_to_utf<char>(buff);
}

int _Camera::AT_GetStringMaxLength(const Feature& feature)
{
    std::ptrdiff_t fi{static_cast<std::ptrdiff_t>(feature)};
    int ret;
    int r = ::AT_GetStringMaxLength(m_dh, sm_featureNames[fi], &ret);
    if(r != AT_SUCCESS)
    {
        std::ostringstream o;
        o << "AT_GetStringMaxLength for feature \"" << boost::locale::conv::utf_to_utf<char>(sm_featureNames[fi]) << "\" failed.";
        throw _AndorException(o.str(), r);
    }
    return ret;
}

void _Camera::AT_QueueBuffer(np::ndarray buff)
{
    int r = ::AT_QueueBuffer(m_dh, reinterpret_cast<AT_U8*>(buff.get_data()), buff.shape(0) * buff.strides(0));
    if(r != AT_SUCCESS)
    {
        std::ostringstream o;
        o << "AT_QueueBuffer with buffer size " << (buff.shape(0) * buff.strides(0)) << " failed.";
        throw _AndorException(o.str(), r);
    }
}

std::uintptr_t _Camera::AT_WaitBuffer(const unsigned int& timeout)
{
    int _buffSize;
    AT_U8* buff;
    int r = ::AT_WaitBuffer(m_dh, &buff, &_buffSize, timeout);
    if(r != AT_SUCCESS)
    {
        std::ostringstream o;
        o << "AT_WaitBuffer with with timeout " << timeout << " failed.";
        throw _AndorException(o.str(), r);
    }
    if(_buffSize <= 0)
    {
        std::ostringstream o;
        o << "AT_WaitBuffer with with timeout " << timeout << " returned a buffer with reported size " << _buffSize << " bytes.";
        throw _AndorException(o.str(), r);
    }
    return reinterpret_cast<uintptr_t>(buff);
}

void _Camera::AT_Flush()
{
    int r = ::AT_Flush(m_dh);
    if(r != AT_SUCCESS)
    {
        throw _AndorException("AT_Flush failed.", r);
    }
}

const wchar_t *_Camera::sm_featureNames[] =
{
    L"Accumulate Count",
    L"Acquisition Start",
    L"Acquisition Stop",
    L"AOI Binning",
    L"AOIHBin",
    L"AOI Height",
    L"AOI Left",
    L"AOI Stride",
    L"AOI Top",
    L"AOIVBin",
    L"AOI Width",
    L"Auxiliary Out Source",
    L"Baseline Level",
    L"Bit Depth",
    L"Buffer Overflow Event",
    L"Bytes Per Pixel",
    L"Camera Acquiring",
    L"Camera Dump",
    L"Camera Model",
    L"Camera Name",
    L"Controller ID",
    L"Cycle Mode",
    L"Device Count",
    L"Device Video Index",
    L"Electronic Shuttering Mode",
    L"Event Enable",
    L"Events Missed Event",
    L"Event Selector",
    L"Exposure Time",
    L"Exposure End Event",
    L"Exposure Start Event",
    L"Fan Speed",
    L"Firmware Version",
    L"Frame Count",
    L"Frame Rate",
    L"Full AOIControl",
    L"Image Size Bytes",
    L"Interface Type",
    L"IO Invert",
    L"IO Selector",
    L"LUT Index",
    L"LUT Value",
    L"Max Interface Transfer Rate",
    L"Metadata Enable",
    L"Metadata Frame",
    L"Metadata Timestamp",
    L"Overlap",
    L"Pixel Correction",
    L"Pixel Encoding",
    L"Pixel Height",
    L"Pixel Readout Rate",
    L"Pixel Width",
    L"Pre Amp Gain",
    L"Pre Amp Gain Channel",
    L"Pre Amp Gain Control",
    L"Pre Amp Gain Selector",
    L"Readout Time",
    L"Rolling Shutter Global Clear",
    L"Row N Exposure End Event",
    L"Row N Exposure Start Event",
    L"Sensor Cooling",
    L"Sensor Height",
    L"Sensor Temperature",
    L"Sensor Width",
    L"Serial Number",
    L"Simple Pre Amp Gain Control",
    L"Software Trigger",
    L"Software Version",
    L"Spurious Noise Filter",
    L"Synchronous Triggering",
    L"Target Sensor Temperature",
    L"Temperature Control",
    L"Temperature Status",
    L"Timestamp Clock",
    L"Timestamp Clock Frequency",
    L"Timestamp Clock Reset",
    L"Trigger Mode",
    L"Vertically Center AOI"
};
