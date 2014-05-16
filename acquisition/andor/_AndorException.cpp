// Copyright 2014 WUSTL ZPLAB

#include "_common.h"
#include "_AndorException.h"

_AndorExceptionBase::_AndorExceptionBase(std::string&& description_)
  : m_description(std::move(description_))
{
}

_AndorExceptionBase::_AndorExceptionBase(const std::string& description_)
  : m_description(description_)
{
}

_AndorExceptionBase::_AndorExceptionBase(const std::wstring& description_)
  : m_description(boost::locale::conv::utf_to_utf<char>(description_))
{
}

const std::string& _AndorExceptionBase::description() const
{
    return m_description;
}

_AndorException::_AndorException(std::string&& description_, const int& errorCode_)
  : _AndorExceptionBase(std::move(description_)),
    m_errorCode(errorCode_)
{
    lookupErrorName(m_errorCode, m_errorName);
}

_AndorException::_AndorException(const std::string& description_, const int& errorCode_)
  : _AndorExceptionBase(description_),
    m_errorCode(errorCode_)
{
    lookupErrorName(m_errorCode, m_errorName);
}

_AndorException::_AndorException(const std::wstring& description_, const int& errorCode_)
  : _AndorExceptionBase(description_),
    m_errorCode(errorCode_)
{
    lookupErrorName(m_errorCode, m_errorName);
}

const int& _AndorException::errorCode() const
{
    return m_errorCode;
}

const std::string& _AndorException::errorName() const
{
    return m_errorName;
}

void _AndorException::lookupErrorName(const int& errorCode, std::string& errorName)
{
    // Note: this may need to be modified when the Andor SDK is updated in order to maintain accurate errorCode to
    // errorName translation
    static const char *errorNames[] =
    {
 /*00*/ "AT_SUCCESS",
 /*01*/ "AT_ERR_NOTINITIALISED",
 /*02*/ "AT_ERR_NOTIMPLEMENTED",
 /*03*/ "AT_ERR_READONLY",
 /*04*/ "AT_ERR_NOTREADABLE",
 /*05*/ "AT_ERR_NOTWRITABLE",
 /*06*/ "AT_ERR_OUTOFRANGE",
 /*07*/ "AT_ERR_INDEXNOTAVAILABLE",
 /*08*/ "AT_ERR_INDEXNOTIMPLEMENTED",
 /*09*/ "AT_ERR_EXCEEDEDMAXSTRINGLENGTH",
 /*10*/ "AT_ERR_CONNECTION",
 /*11*/ "AT_ERR_NODATA",
 /*12*/ "AT_ERR_INVALIDHANDLE",
 /*13*/ "AT_ERR_TIMEDOUT",
 /*14*/ "AT_ERR_BUFFERFULL",
 /*15*/ "AT_ERR_INVALIDSIZE",
 /*16*/ "AT_ERR_INVALIDALIGNMENT",
 /*17*/ "AT_ERR_COMM",
 /*18*/ "AT_ERR_STRINGNOTAVAILABLE",
 /*19*/ "AT_ERR_STRINGNOTIMPLEMENTED",
 /*20*/ "AT_ERR_NULL_FEATURE",
 /*21*/ "AT_ERR_NULL_HANDLE",
 /*22*/ "AT_ERR_NULL_IMPLEMENTED_VAR",
 /*23*/ "AT_ERR_NULL_READABLE_VAR",
 /*24*/ "AT_ERR_NULL_READONLY_VAR",
 /*25*/ "AT_ERR_NULL_WRITABLE_VAR",
 /*26*/ "AT_ERR_NULL_MINVALUE",
 /*27*/ "AT_ERR_NULL_MAXVALUE",
 /*28*/ "AT_ERR_NULL_VALUE",
 /*29*/ "AT_ERR_NULL_STRING",
 /*30*/ "AT_ERR_NULL_COUNT_VAR",
 /*31*/ "AT_ERR_NULL_ISAVAILABLE_VAR",
 /*32*/ "AT_ERR_NULL_MAXSTRINGLENGTH",
 /*33*/ "AT_ERR_NULL_EVCALLBACK",
 /*34*/ "AT_ERR_NULL_QUEUE_PTR",
 /*35*/ "AT_ERR_NULL_WAIT_PTR",
 /*36*/ "AT_ERR_NULL_PTRSIZE",
 /*37*/ "AT_ERR_NOMEMORY",
 /*38*/ "AT_ERR_DEVICEINUSE"
    };
    static const std::size_t errorNamesCount = sizeof(errorNames) / sizeof(*errorNames);

    if(errorCode >= 0 && static_cast<std::size_t>(errorCode) < errorNamesCount)
    {
        errorName = errorNames[errorCode];
    }
    else if(errorCode == 100)
    {
        errorName = "AT_ERR_HARDWARE_OVERFLOW";
    }
    else
    {
        errorName = "UNKNOWN ERROR CODE";
    }
}
