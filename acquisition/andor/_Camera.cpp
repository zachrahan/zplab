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
    std::wcerr << sm_featureNames[fi] << std::endl;
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
    _GilScopedRelease _gilScopedRelease;
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

_Camera::SimplePreAmp _Camera::simplePreAmp() const
{
    int v = const_cast<_Camera*>(this)->AT_GetEnumIndex(Feature::SimplePreAmpGainControl);
    if(v < int(SimplePreAmp::_Begin) || v >= int(SimplePreAmp::_End))
    {
        std::ostringstream o;
        o << "AT_GetEnumIndex returned " << v << " for SimplePreAmpGainControl, which is not in the interval corresponding ";
        o << "to known values, [" << static_cast<int>(SimplePreAmp::_Begin) << ", " << static_cast<int>(SimplePreAmp::_End) << ").";
        throw _AndorExceptionBase(o.str());
    }
    return SimplePreAmp(v);
}

void _Camera::simplePreAmp(const SimplePreAmp& simplePreAmp_)
{
    AT_SetEnumIndex(Feature::SimplePreAmpGainControl, int(simplePreAmp_));
}

_Camera::Shutter _Camera::shutter() const
{
    int v = const_cast<_Camera*>(this)->AT_GetEnumIndex(Feature::ElectronicShutteringMode);
    if(v < int(Shutter::_Begin) || v >= int(Shutter::_End))
    {
        std::ostringstream o;
        o << "AT_GetEnumIndex returned " << v << " for ElectronicShutteringMode, which is not in the interval corresponding ";
        o << "to known values, [" << static_cast<int>(Shutter::_Begin) << ", " << static_cast<int>(Shutter::_End) << ").";
        throw _AndorExceptionBase(o.str());
    }
    return Shutter(v);
}

void _Camera::shutter(const Shutter& shutter_)
{
    AT_SetEnumIndex(Feature::ElectronicShutteringMode, int(shutter_));
}

_Camera::TriggerMode _Camera::triggerMode() const
{
    int v = const_cast<_Camera*>(this)->AT_GetEnumIndex(Feature::TriggerMode);
    if(v < int(TriggerMode::_Begin) || v >= int(TriggerMode::_End))
    {
        std::ostringstream o;
        o << "AT_GetEnumIndex returned " << v << " for TriggerMode, which is not in the interval corresponding ";
        o << "to known values, [" << static_cast<int>(TriggerMode::_Begin) << ", " << static_cast<int>(TriggerMode::_End) << ").";
        throw _AndorExceptionBase(o.str());
    }
    return TriggerMode(v);
}

void _Camera::triggerMode(const TriggerMode& triggerMode_)
{
    AT_SetEnumIndex(Feature::TriggerMode, int(triggerMode_));
}

_Camera::TemperatureStatus _Camera::temperatureStatus() const
{
    int v = const_cast<_Camera*>(this)->AT_GetEnumIndex(Feature::TemperatureStatus);
    if(v < int(TemperatureStatus::_Begin) || v >= int(TemperatureStatus::_End))
    {
        std::ostringstream o;
        o << "AT_GetEnumIndex returned " << v << " for TemperatureStatus, which is not in the interval corresponding ";
        o << "to known values, [" << static_cast<int>(TemperatureStatus::_Begin) << ", " << static_cast<int>(TemperatureStatus::_End) << ").";
        throw _AndorExceptionBase(o.str());
    }
    return TemperatureStatus(v);
}

_Camera::Binning _Camera::binning() const
{
    int v = const_cast<_Camera*>(this)->AT_GetEnumIndex(Feature::AOIBinning);
    if(v < int(Binning::_Begin) || v >= int(Binning::_End))
    {
        std::ostringstream o;
        o << "AT_GetEnumIndex returned " << v << " for AOIBinning, which is not in the interval corresponding ";
        o << "to known values, [" << static_cast<int>(Binning::_Begin) << ", " << static_cast<int>(Binning::_End) << ").";
        throw _AndorExceptionBase(o.str());
    }
    return Binning(v);
}

void _Camera::binning(const Binning& binning_)
{
    AT_SetEnumIndex(Feature::AOIBinning, int(binning_));
}

_Camera::AuxiliaryOutSource _Camera::auxiliaryOutSource() const
{
    int v = const_cast<_Camera*>(this)->AT_GetEnumIndex(Feature::AuxiliaryOutSource);
    if(v < int(AuxiliaryOutSource::_Begin) || v >= int(AuxiliaryOutSource::_End))
    {
        std::ostringstream o;
        o << "AT_GetEnumIndex returned " << v << " for AuxiliaryOutSource, which is not in the interval corresponding ";
        o << "to known values, [" << static_cast<int>(AuxiliaryOutSource::_Begin) << ", " << static_cast<int>(AuxiliaryOutSource::_End) << ").";
        throw _AndorExceptionBase(o.str());
    }
    return AuxiliaryOutSource(v);
}

void _Camera::auxiliaryOutSource(const AuxiliaryOutSource& auxiliaryOutSource_)
{
    AT_SetEnumIndex(Feature::AuxiliaryOutSource, int(auxiliaryOutSource_));
}

_Camera::CycleMode _Camera::cycleMode() const
{
    int v = const_cast<_Camera*>(this)->AT_GetEnumIndex(Feature::CycleMode);
    if(v < int(CycleMode::_Begin) || v >= int(CycleMode::_End))
    {
        std::ostringstream o;
        o << "AT_GetEnumIndex returned " << v << " for CycleMode, which is not in the interval corresponding ";
        o << "to known values, [" << static_cast<int>(CycleMode::_Begin) << ", " << static_cast<int>(CycleMode::_End) << ").";
        throw _AndorExceptionBase(o.str());
    }
    return CycleMode(v);
}

void _Camera::cycleMode(const CycleMode& cycleMode_)
{
    AT_SetEnumIndex(Feature::CycleMode, int(cycleMode_));
}

_Camera::FanSpeed _Camera::fanSpeed() const
{
    int v = const_cast<_Camera*>(this)->AT_GetEnumIndex(Feature::FanSpeed);
    if(v < int(FanSpeed::_Begin) || v >= int(FanSpeed::_End))
    {
        std::ostringstream o;
        o << "AT_GetEnumIndex returned " << v << " for FanSpeed, which is not in the interval corresponding ";
        o << "to known values, [" << static_cast<int>(FanSpeed::_Begin) << ", " << static_cast<int>(FanSpeed::_End) << ").";
        throw _AndorExceptionBase(o.str());
    }
    return FanSpeed(v);
}

void _Camera::fanSpeed(const FanSpeed& fanSpeed_)
{
    AT_SetEnumIndex(Feature::FanSpeed, int(fanSpeed_));
}

_Camera::PixelEncoding _Camera::pixelEncoding() const
{
    int v = const_cast<_Camera*>(this)->AT_GetEnumIndex(Feature::PixelEncoding);
    if(v < int(PixelEncoding::_Begin) || v >= int(PixelEncoding::_End))
    {
        std::ostringstream o;
        o << "AT_GetEnumIndex returned " << v << " for PixelEncoding, which is not in the interval corresponding ";
        o << "to known values, [" << static_cast<int>(PixelEncoding::_Begin) << ", " << static_cast<int>(PixelEncoding::_End) << ").";
        throw _AndorExceptionBase(o.str());
    }
    return PixelEncoding(v);
}

const wchar_t *_Camera::sm_featureNames[] =
{
    L"AccumulateCount",
    L"AcquisitionStart",
    L"AcquisitionStop",
    L"AOIBinning",
    L"AOIHBin",
    L"AOIHeight",
    L"AOILeft",
    L"AOIStride",
    L"AOITop",
    L"AOIVBin",
    L"AOIWidth",
    L"AuxiliaryOutSource",
    L"BaselineLevel",
    L"BitDepth",
    L"BufferOverflowEvent",
    L"BytesPerPixel",
    L"CameraAcquiring",
    L"CameraDump",
    L"CameraModel",
    L"CameraName",
    L"ControllerID",
    L"CycleMode",
    L"DeviceCount",
    L"DeviceVideoIndex",
    L"ElectronicShutteringMode",
    L"EventEnable",
    L"EventsMissedEvent",
    L"EventSelector",
    L"ExposureTime",
    L"ExposureEndEvent",
    L"ExposureStartEvent",
    L"FanSpeed",
    L"FirmwareVersion",
    L"FrameCount",
    L"FrameRate",
    L"FullAOIControl",
    L"ImageSizeBytes",
    L"InterfaceType",
    L"IOInvert",
    L"IOSelector",
    L"LUTIndex",
    L"LUTValue",
    L"MaxInterfaceTransferRate",
    L"MetadataEnable",
    L"MetadataFrame",
    L"MetadataTimestamp",
    L"Overlap",
    L"PixelCorrection",
    L"PixelEncoding",
    L"PixelHeight",
    L"PixelReadoutRate",
    L"PixelWidth",
    L"PreAmpGain",
    L"PreAmpGainChannel",
    L"PreAmpGainControl",
    L"PreAmpGainSelector",
    L"ReadoutTime",
    L"RollingShutterGlobalClear",
    L"RowNExposureEndEvent",
    L"RowNExposureStartEvent",
    L"SensorCooling",
    L"SensorHeight",
    L"SensorTemperature",
    L"SensorWidth",
    L"SerialNumber",
    L"SimplePreAmpGainControl",
    L"SoftwareTrigger",
    L"SoftwareVersion",
    L"SpuriousNoiseFilter",
    L"SynchronousTriggering",
    L"TargetSensorTemperature",
    L"TemperatureControl",
    L"TemperatureStatus",
    L"TimestampClock",
    L"TimestampClockFrequency",
    L"TimestampClockReset",
    L"TriggerMode",
    L"VerticallyCenterAOI"
};

const wchar_t *_Camera::sm_simplePreAmpNames[] =
{
    L"12-bit (high well capacity)",
    L"12-bit (low noise)",
    L"16-bit (low noise & high well capacity)"
};

const wchar_t *_Camera::sm_shutterNames[] =
{
    L"Rolling",
    L"Global"
};

const wchar_t *_Camera::sm_triggerModeNames[] =
{
    L"Internal",
    L"External Level Transition",
    L"External Start",
    L"External Exposure",
    L"Software",
    L"Advanced",
    L"External"
};

const wchar_t *_Camera::sm_temperatureStatusNames[] =
{
    L"Cooler Off",
    L"Stabilised",
    L"Cooling",
    L"Drift",
    L"Not Stabilised",
    L"Fault"
};

const wchar_t *_Camera::sm_binningNames[] =
{
    L"1x1",
    L"2x2",
    L"3x3",
    L"4x4",
    L"8x8"
};

const wchar_t *_Camera::sm_auxiliaryOutSourceNames[] =
{
    L"FireRow1",
    L"FireRowN",
    L"FireAll",
    L"FireAny"
};

const wchar_t *_Camera::sm_cycleModeNames[] =
{
    L"Fixed",
    L"Continuous"
};

const wchar_t *_Camera::sm_fanSpeedNames[] =
{
    L"Off",
    L"On"
};

const wchar_t *_Camera::sm_pixelEncodingNames[] =
{
    L"Mono12",
    L"Mono12Packed",
    L"Mono16",
    L"RGB8Packed",
    L"Mono12Coded",
    L"Mono12CodedPacked",
    L"Mono22Parallel",
    L"Mono22PackedParallel",
    L"Mono8",
    L"Mono32"
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
