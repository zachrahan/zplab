// Copyright 2014 WUSTL ZPLAB

#include "_common.h"
#include "_AndorException.h"
#include "_Camera.h"
#include "_GilScopedRelease.h"

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

const wchar_t* _Camera::lookupFeatureName(const Feature& feature)
{
    return sm_featureNames[static_cast<std::ptrdiff_t>(feature)];
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

int AT_EXP_CONV _Camera::atCallbackWrapper(AT_H dh, const AT_WC* calledFeatureName, void* crtvp)
{
    int ret{AT_CALLBACK_SUCCESS};
    _CallbackRegistrationToken& crt(*reinterpret_cast<_CallbackRegistrationToken*>(crtvp));
    const wchar_t* requestedFeatureName{_Camera::lookupFeatureName(crt.m_feature)};

    // Compare requested and called feature strings without regard for whitespace discrepancies
    bool same{true}, cfne, rfne;
    for(const wchar_t* cfn{calledFeatureName}, *rfn{requestedFeatureName};;)
    {
        if(*cfn == L' ')
        {
            // Skip space in calledFeature
            ++cfn;
            continue;
        }
        if(*rfn == L' ')
        {
            // Skip space in requestedFeature
            ++rfn;
            continue;
        }
        cfne = *cfn == L'\0';
        rfne = *rfn == L'\0';
        if(cfne != rfne)
        {
            // Encountered the end of one string while still attempting to match a non-whitespace character in the
            // other
            same = false;
            break;
        }
        if(cfne) // Note: cfne == rfne at this point; checking rfne as well would be redundant
        {
            // Reached the end of both strings without encountering a mismatch
            break;
        }
        if(*cfn != *rfn)
        {
            // Encountered mismatch between non-whitespace characters
            same = false;
            break;
        }
        // Non-whitespace characters in both strings matched.  Advance to next character in both strings.
        ++cfn;
        ++rfn;
    }

    if(!same)
    {
        std::wostringstream o;
        o << L"Callback specified for feature \"" << requestedFeatureName
          << L"\" was instead called by Andor SDK with feature string \"" << calledFeatureName
          << L"\".  Note that spaces do not interfere with correct feature string identification.";
        throw _AndorExceptionBase(o.str());
    }
    if(dh != crt.m_camera.m_dh)
    {
        std::wostringstream o;
        o << L"Callback for feature \"" << requestedFeatureName << L"\" on device with Andor SDK handle "
          << crt.m_camera.m_dh << L" was instead called by Andor SDK with handle " << dh << L'.';
        throw _AndorExceptionBase(o.str());
    }

    // From Andor SDK3 manual: "As soon as this callback is registered a single callback will be made immediately to
    // allow the callback handling code to perform any Initialisation code to set up monitoring of the feature."
    //
    // We do not want this; we want to be called if and only if our feature changed.  So, this unwanted
    // initialization call, termed the "precall," is noted and ignored and does not result in the callback supplied
    // by the user being executed.
    if(!crt.m_precalled)
    {
        crt.m_precalled = true;
    }
    else
    {
        if(!crt.m_callback(crt.m_feature))
        {
            // Any old error code that isn't zero should suffice, but this one is hopefully different from any used
            // by the Andor SDK and should thus be identifiable should it need to be.
            ret = std::numeric_limits<int>::min() + 4242;
        }
    }
    return ret;
}

std::shared_ptr<_Camera::_CallbackRegistrationToken> _Camera::AT_RegisterFeatureCallback(const Feature& feature, const std::function<bool(Feature)>& callback)
{
    std::ptrdiff_t fi{static_cast<std::ptrdiff_t>(feature)};
    std::shared_ptr<_CallbackRegistrationToken> crt{new _CallbackRegistrationToken{*this, feature, callback}};
    int r = ::AT_RegisterFeatureCallback(m_dh, sm_featureNames[fi], &_Camera::atCallbackWrapper, reinterpret_cast<void*>(crt.get()));
    if(r != AT_SUCCESS)
    {
        std::wostringstream o;
        o << "AT_RegisterFeatureCallback call to Andor SDK for feature \"" << sm_featureNames[fi] << "\" failed.";
        throw _AndorException(o.str(), r);
    }
    m_crts.insert(crt);
    return crt;
}

static bool AT_RegisterFeatureCallbackPyWrapperHelper(py::object& pyCallback, _Camera::Feature feature)
{
    return py::extract<bool>(pyCallback(feature));
}

std::shared_ptr<_Camera::_CallbackRegistrationToken> _Camera::AT_RegisterFeatureCallbackPyWrapper(const Feature& feature, py::object pyCallback)
{
    // The following should work, but does not compile on g++ 4.8.2-r1.
//  AT_RegisterFeatureCallback(feature, [=](Feature feature)mutable{return py::extract<bool>(pyCallback(feature));});
    // So we use a static wrapper function for executing the py::extract portion (the part that causes compilation
    // problems).
    return AT_RegisterFeatureCallback(feature, [pyCallback](Feature feature_)mutable{return AT_RegisterFeatureCallbackPyWrapperHelper(pyCallback, feature_);});
}

void _Camera::AT_UnregisterFeatureCallback(const std::shared_ptr<_CallbackRegistrationToken>& crt)
{
    std::ptrdiff_t fi{static_cast<std::ptrdiff_t>(crt->m_feature)};
    if(&crt->m_camera != this)
    {
        std::wostringstream o;
        o << L"AT_UnregisterFeatureCallback called for feature \"" << sm_featureNames[fi] 
          << L"\" for different _Camera instance's callback token.";
        throw _AndorExceptionBase(o.str());
    }
    Crts::iterator it{m_crts.find(crt)};
    if(it == m_crts.end())
    {
        std::wostringstream o;
        o << L"AT_UnregisterFeatureCallback called for feature \"" << sm_featureNames[fi] 
          << L"\" for callback that is not registered.  Perhaps AT_UnregisterFeatureCallback was called twice for the same callback token.";
        throw _AndorExceptionBase(o.str());
    }
    m_crts.erase(it);
    int r = ::AT_UnregisterFeatureCallback(m_dh, sm_featureNames[fi], &_Camera::atCallbackWrapper, reinterpret_cast<void*>(crt.get()));
    if(r != AT_SUCCESS)
    {
        std::wostringstream o;
        o << "AT_UnregisterFeatureCallback call to Andor SDK for feature \"" << sm_featureNames[fi] << "\" failed.";
        throw _AndorException(o.str(), r);
    }
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
    _GilScopedRelease();
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

_Camera::_CallbackRegistrationToken::_CallbackRegistrationToken(_Camera& camera_, const Feature& feature_, const std::function<bool(Feature)>& callback_)
  : m_camera(camera_),
    m_feature(feature_),
    m_callback(callback_),
    m_precalled(false)
{
    std::wcerr << L"_Camera::_CallbackRegistrationToken::_CallbackRegistrationToken()  " << sm_featureNames[static_cast<std::ptrdiff_t>(m_feature)] << std::endl;
}

_Camera::_CallbackRegistrationToken::~_CallbackRegistrationToken()
{
    std::wcerr << L"_Camera::_CallbackRegistrationToken::~_CallbackRegistrationToken() " << sm_featureNames[static_cast<std::ptrdiff_t>(m_feature)] << std::endl;
}

bool _Camera::_CallbackRegistrationToken::operator == (const _CallbackRegistrationToken& rhs) const
{
    return this == &rhs;
}

bool _Camera::_CallbackRegistrationToken::operator != (const _CallbackRegistrationToken& rhs) const
{
    return this != &rhs;
}
