// Copyright 2014 WUSTL ZPLAB

#pragma once
#include "_common.h"

class _AndorExceptionBase
{
public:
    explicit _AndorExceptionBase(std::string&& description_);
    explicit _AndorExceptionBase(const std::string& description_ = std::string(""));

    const std::string& description() const;

protected:
    std::string m_description;
};

class _AndorException
  : public _AndorExceptionBase
{
public:
    _AndorException(std::string&& description_, const int& errorCode_);
    _AndorException(const std::string& description_, const int& errorCode_);

    const int& errorCode() const;
    const std::string& errorName() const;

    static void lookupErrorName(const int& errorCode, std::string& errorName);

protected:
    int m_errorCode;
    std::string m_errorName;
};

